import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.data.csdi import fetch_source
from backend.app.data.sources import CATEGORIES, SOURCES
from backend.app.models.venue import Venue, VenueCollection
from backend.app.services.photo_service import PhotoService
from backend.app.utils.compose import compose

logger = logging.getLogger(__name__)
REFRESH_SECONDS = 3600
CONCURRENCY = 8


class VenueService:
    """Facility layers cached in Redis for an hour, with per-layer stale fallback and serialized refreshes."""

    def __init__(self, cache: RedisCache, client: httpx.AsyncClient, photos: PhotoService,
                 throttle_seconds: int = 60):
        self.cache = cache
        self.client = client
        self.photos = photos
        self.throttle_seconds = throttle_seconds
        self.layers: dict[str, dict] = {}
        self.errors: list[str] = []
        self.lock = asyncio.Lock()

    @staticmethod
    def _key(source_key: str) -> str:
        return f"venues:layer:{source_key}"

    async def load(self) -> None:
        """Restore layers persisted in Redis; unknown or corrupt entries are ignored."""
        for source in SOURCES:
            layer = await self.cache.get_json(self._key(source.key))
            try:
                self.layers[source.key] = {**layer, "items": [Venue.model_validate(v) for v in layer["items"]]}
            except (ValueError, KeyError, TypeError):
                continue

    async def _persist(self, source_key: str) -> None:
        layer = self.layers[source_key]
        await self.cache.set_json(self._key(source_key), {**layer, "items": [i.model_dump() for i in layer["items"]]})

    async def refresh_if_due(self) -> None:
        async with self.lock:
            now = time.time()
            due = [s for s in SOURCES if now - self.layers.get(s.key, {}).get("time", 0) >= REFRESH_SECONDS]
            if not due:
                return
            if self.throttle_seconds and not await self.cache.set_if_absent("venues:attempt", self.throttle_seconds):
                return
            gate = asyncio.Semaphore(CONCURRENCY)

            async def pull(source):
                async with gate:
                    return await fetch_source(source, self.client)

            results = await asyncio.gather(*(pull(s) for s in due), return_exceptions=True)
            errors = []
            for source, result in zip(due, results):
                if isinstance(result, BaseException):
                    logger.error("Facility sync failed: %s", source.key, exc_info=result)
                    errors.append(source.key)
                    continue
                items, skipped = result
                self.layers[source.key] = {"time": now, "items": items, "skipped": skipped}
                await self._persist(source.key)
            self.errors = errors

    async def list_venues(self) -> VenueCollection:
        await self.refresh_if_due()
        collection = self._collection()
        return collection.model_copy(update={"items": await self.photos.enrich(collection.items)})

    def _collection(self) -> VenueCollection:
        items = compose({key: layer["items"] for key, layer in self.layers.items()})
        status = "error" if not self.layers and self.errors else "not_synced" if not self.layers else "partial" if self.errors or len(self.layers) < len(SOURCES) else "ready"
        timestamp = min((v["time"] for v in self.layers.values()), default=None)
        return VenueCollection(
            data_status=status, items=items, total=len(items) if self.layers else None,
            updated_at=datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None,
            source_errors=self.errors, skipped_records=sum(v.get("skipped", 0) for v in self.layers.values()),
            message="部分图层更新失败；保留已有数据，可稍后重试。" if self.errors and self.layers else "暂时无法获取场地，请稍后重试。" if self.errors else "设施图层记录可能重叠；记录数不等于独立场所数。" if self.layers else "设施数据尚未同步。",
        )

    @staticmethod
    def _category_sources() -> list[dict]:
        return [{
            "key": c.key, "name_zh": c.name_zh, "group": c.group,
            "research_record_count": sum(s.research_record_count for s in SOURCES if s.category_key == c.key),
            "research_checked_on": "2026-10-22", "count_provenance": "raw_layer_records",
            "layers": [s.to_dict() for s in SOURCES if s.category_key == c.key],
        } for c in CATEGORIES]

    def data_status(self) -> dict:
        return {
            "facility_sync": self._collection().data_status,
            "booking_sync": "not_connected", "unique_venue_total": None,
            "sources": self._category_sources(),
            "notes": ["Layers can overlap; do not sum counts as unique venues.",
                      "Missing availability means unknown, never full.",
                      "Published booking availability is not on-site occupancy."],
        }

    def facility_records(self) -> list[Venue]:
        """Raw cached facilities, used to enrich booking venues without triggering a CSDI fetch."""
        return [v for layer in self.layers.values() for v in layer["items"]]
