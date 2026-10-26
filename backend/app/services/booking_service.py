"""Official SmartPLAY snapshots cached in Redis. Missing rows/counts remain unknown, not zero."""
import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.data.booking_catalog import SOURCE_CATALOG, SOURCE_URLS, SPORTS
from backend.app.models.booking import BookingCollection
from backend.app.services.photo_service import PhotoService
from backend.app.services.venue_service import VenueService
from backend.app.utils.booking import normalize_rows

logger = logging.getLogger(__name__)
FRESH_SECONDS = 300


class BookingService:
    def __init__(self, cache: RedisCache, client: httpx.AsyncClient, venues: VenueService,
                 photos: PhotoService, throttle_seconds: int = 60):
        self.cache = cache
        self.client = client
        self.venues = venues
        self.photos = photos
        self.throttle_seconds = throttle_seconds
        self.snapshots: dict[str, BookingCollection] = {}
        self.locks = {sport: asyncio.Lock() for sport in SPORTS}

    @property
    def catalog(self) -> dict:
        return SOURCE_CATALOG

    @property
    def sports(self) -> dict[str, str]:
        return SPORTS

    async def _with_venue_photos(self, collection: BookingCollection) -> BookingCollection:
        if not collection.venues:
            return collection
        enriched = await self.photos.enrich([item.venue for item in collection.venues])
        venues = [item.model_copy(update={"venue": venue}) for item, venue in zip(collection.venues, enriched)]
        return collection.model_copy(update={"venues": venues})

    @staticmethod
    def _error(sport: str, url: str) -> BookingCollection:
        return BookingCollection(sport=sport, sport_label=SPORTS[sport], status="error", source_url=url,
                                 message="暂时无法获取官方余量，请稍后重试。")

    async def get(self, sport: str) -> BookingCollection:
        async with self.locks[sport]:
            if sport not in self.snapshots:
                raw = await self.cache.get_bytes(f"bookings:{sport}")
                if raw:
                    try:
                        self.snapshots[sport] = BookingCollection.model_validate_json(raw)
                    except ValueError:
                        pass
            cached = self.snapshots.get(sport)
            if cached:
                cached.sport_label = SPORTS[sport]
                cached = await self._with_venue_photos(cached)
                self.snapshots[sport] = cached
            now = time.time()
            age = now - datetime.fromisoformat(cached.fetched_at).timestamp() if cached and cached.fetched_at else float("inf")
            if age < FRESH_SECONDS:
                return cached
            url = SOURCE_URLS[sport]
            if self.throttle_seconds and not await self.cache.set_if_absent(f"bookings:attempt:{sport}", self.throttle_seconds):
                if cached:
                    return cached.model_copy(update={"status": "stale", "message": "更新失败，正在显示旧快照。"})
                return self._error(sport, url)
            try:
                response = await self.client.get(url, timeout=35)
                response.raise_for_status()
                # Only use already cached facility metadata; do not make booking fetch depend on CSDI availability.
                venues = normalize_rows(response.json(), sport, self.venues.facility_records())
                collection = BookingCollection(sport=sport, sport_label=SPORTS[sport], status="ready", source_url=url,
                    fetched_at=datetime.now(timezone.utc).isoformat(), source_updated_at=response.headers.get("last-modified"),
                    dates=sorted({s.date for v in venues for s in v.slots}), venues=venues,
                    message="官方快照每5分钟更新；抓取时间不等于官方生成时间。空位以康体通实际预订结果为准。")
                await self.cache.set_bytes(f"bookings:{sport}", collection.model_dump_json().encode())
                collection = await self._with_venue_photos(collection)
                self.snapshots[sport] = collection
                return collection
            except Exception:
                logger.exception("Booking sync failed: %s", sport)
                if cached:
                    return cached.model_copy(update={"status": "stale", "message": "官方余量更新失败，以下为旧快照，请勿视作实时可订。"})
                return self._error(sport, url)
