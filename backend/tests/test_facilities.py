import asyncio

import httpx
import pytest

from backend.app.cache.redis_cache import RedisCache
from backend.app.data.csdi import fetch_source, normalize
from backend.app.data.sources import SOURCES
from backend.app.services.photo_service import PhotoService
from backend.app.services.venue_service import VenueService


def feature(oid=1):
    return {"id": oid, "geometry": {"type": "Point", "coordinates": [114.17, 22.32]},
            "properties": {"OBJECTID": oid, "NameTC": "測試體育館", "AddressTC": "九龍測試道1號", "TelephoneTC": "N.A."}}


def make_service(cache=None, throttle=0):
    cache = cache or RedisCache(None)
    client = httpx.AsyncClient()
    photos = PhotoService(cache, client)

    async def no_refresh():
        return None
    photos.refresh = no_refresh
    return VenueService(cache, client, photos, throttle_seconds=throttle)


def test_normalizes_address_and_missing_fields():
    venue = normalize(SOURCES[0], feature())
    assert venue.address_zh == "九龍測試道1號"
    assert venue.telephone is None
    assert venue.longitude == 114.17
    assert not venue.point_is_entrance
    with pytest.raises(ValueError):
        normalize(SOURCES[0], {**feature(), "geometry": None})


def test_other_layer_schemas():
    f = feature()
    f["properties"] = {"OBJECTID": 2, "Name_cn": "公園", "Address_cn": "公園道", "District_cn": "中西區"}
    assert normalize(SOURCES[2], f).address_zh == "公園道"
    f["properties"] = {"OBJECTID": 2, "NAME_TC": "球場", "ADDRESS_TC": "球場道", "No__of_Basketball_Courts_TC": 3}
    assert normalize(SOURCES[3], f).court_count == 3


def test_pagination(monkeypatch):
    offsets = []

    async def get(self, url, params=None, **kwargs):
        offsets.append(params["resultOffset"])
        return httpx.Response(200, request=httpx.Request("GET", url), json={
            "type": "FeatureCollection", "features": [feature(len(offsets))],
            "properties": {"exceededTransferLimit": len(offsets) == 1}})
    monkeypatch.setattr(httpx.AsyncClient, "get", get)

    async def run():
        async with httpx.AsyncClient() as client:
            return await fetch_source(SOURCES[0], client)
    items, skipped = asyncio.run(run())
    assert offsets == [0, 1]
    assert len(items) == 2 and skipped == 0


def test_cache_and_stale_fallback(monkeypatch):
    calls = []

    async def fetch(source, client):
        calls.append(source.key)
        return [normalize(source, feature())], 0
    monkeypatch.setattr("backend.app.services.venue_service.fetch_source", fetch)
    cache = RedisCache(None)
    service = make_service(cache)

    async def run():
        assert (await service.list_venues()).data_status == "ready"
        assert (await service.list_venues()).total == 7
        assert len(calls) == len(SOURCES)
        for layer in service.layers.values():
            layer["time"] = 1

        async def fail(source, client):
            raise RuntimeError("upstream unavailable")
        monkeypatch.setattr("backend.app.services.venue_service.fetch_source", fail)
        result = await service.list_venues()
        assert result.data_status == "partial"
        assert result.total == 7
        assert len(result.source_errors) == len(SOURCES)
        restored = make_service(cache)
        await restored.load()
        assert restored._collection().total == 7
    asyncio.run(run())


def test_all_sources_failed_is_not_empty_success(monkeypatch):
    async def fail(source, client):
        raise RuntimeError("offline")
    monkeypatch.setattr("backend.app.services.venue_service.fetch_source", fail)
    result = asyncio.run(make_service().list_venues())
    assert result.data_status == "error"
    assert result.total is None


def test_throttle_blocks_repeat_upstream_attempts(monkeypatch):
    calls = []

    async def fail(source, client):
        calls.append(source.key)
        raise RuntimeError("offline")
    monkeypatch.setattr("backend.app.services.venue_service.fetch_source", fail)
    service = make_service(throttle=60)

    async def run():
        await service.list_venues()
        await service.list_venues()
    asyncio.run(run())
    assert len(calls) == len(SOURCES)
