import asyncio

import httpx
import pytest

from backend.app.cache.redis_cache import RedisCache
from backend.app.data.booking_catalog import SOURCE_URLS, SPORTS
from backend.app.services.booking_service import BookingService
from backend.app.utils.booking import normalize_rows


def row(**changes):
    return {"District_Name_TC": "中西區", "Venue_Name_TC": "測試體育館", "Venue_Name_EN": "Test Centre",
            "Venue_Address_TC": "測試街1號", "Venue_Address_EN": "1 Test Road", "Venue_Phone_No.": "12345678",
            "Venue_Longitude": "114.17", "Venue_Latitude": "22.3", "Facility_Type_Name_TC": "羽毛球場",
            "Facility_Location_Name_TC": "主場", "Available_Date": "2026-10-22",
            "Session_Start_Time": "07:00", "Session_End_Time": "08:00", "Available_Courts": "2", **changes}


class FakeVenues:
    def facility_records(self):
        return []


class FakePhotos:
    async def enrich(self, venues):
        return venues


def test_duplicate_slots_not_counted_twice_and_locations_retained():
    data = normalize_rows([row(), row(), row(Facility_Location_Name_TC="副場", Available_Courts="3")], "badminton", [])
    assert len(data) == 1
    assert len(data[0].slots) == 2
    assert sum(s.remaining for s in data[0].slots) == 5
    with pytest.raises(ValueError):
        normalize_rows([row(), row(Available_Courts="9")], "badminton", [])


def test_unknown_and_zero_are_distinct_and_missing_coordinates_preserved():
    missing = row(Available_Courts="N.A.")
    missing.pop("Venue_Longitude")
    missing.pop("Venue_Latitude")
    data = normalize_rows([missing], "badminton", [])
    assert data[0].venue.latitude is None
    assert data[0].slots[0].remaining is None
    assert normalize_rows([row(Available_Courts="0")], "badminton", [])[0].slots[0].remaining == 0


def test_empty_file_is_not_zero_availability():
    with pytest.raises(ValueError):
        normalize_rows([], "badminton", [])


def test_cache_failure_fallback_and_recovery(monkeypatch):
    calls = []

    async def get(self, url, **kwargs):
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("GET", url), json=[row()])
    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    service = BookingService(RedisCache(None), httpx.AsyncClient(), FakeVenues(), FakePhotos(), throttle_seconds=0)

    async def run():
        global_get = httpx.AsyncClient.get
        first = await service.get("badminton")
        assert first.status == "ready"
        assert (await service.get("badminton")) == first
        assert len(calls) == 1
        service.snapshots["badminton"].fetched_at = "2026-01-01T00:00:00+00:00"

        async def fail(self, *args, **kwargs):
            raise httpx.ConnectError("offline")
        monkeypatch.setattr(httpx.AsyncClient, "get", fail)
        stale = await service.get("badminton")
        assert stale.status == "stale" and stale.venues
        assert (await service.get("tennis")).status == "error"
        assert (await service.get("tennis")).venues == []
        monkeypatch.setattr(httpx.AsyncClient, "get", global_get)
        assert (await service.get("badminton")).status == "ready"
    asyncio.run(run())


def test_catalog_exposes_every_supported_source(make_app):
    from fastapi.testclient import TestClient
    with TestClient(make_app()) as client:
        response = client.get("/api/v1/availability/sports")
        assert response.status_code == 200
        catalog = response.json()
        assert {source["key"] for source in catalog["items"]} == set(SPORTS)
        assert len(catalog["items"]) == 5
        assert catalog["lcsd_dataset_count"] == 124
        assert all(source["source_url"] == SOURCE_URLS[source["key"]] for source in catalog["items"])
        assert client.get("/api/v1/availability?sport=unsupported").status_code == 422
