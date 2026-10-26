"""Dependency container: one shared HTTP client, one cache, one instance of each service."""
from dataclasses import dataclass

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.config.settings import Settings
from backend.app.services.booking_service import BookingService
from backend.app.services.photo_service import PhotoService
from backend.app.services.programme_service import ProgrammeService
from backend.app.services.venue_service import VenueService


@dataclass
class Container:
    settings: Settings
    cache: RedisCache
    client: httpx.AsyncClient
    photos: PhotoService
    venues: VenueService
    bookings: BookingService
    programmes: ProgrammeService

    async def aclose(self) -> None:
        await self.client.aclose()
        await self.cache.aclose()


async def build_container(settings: Settings, cache: RedisCache | None = None) -> Container:
    cache = cache or RedisCache.from_url(settings.redis_url, settings.cache_prefix)
    client = httpx.AsyncClient(trust_env=False, timeout=30)
    photos = PhotoService(cache, client)
    venues = VenueService(cache, client, photos)
    container = Container(settings, cache, client, photos, venues,
                          BookingService(cache, client, venues, photos),
                          ProgrammeService(cache, client))
    for service in (photos, venues, container.programmes):
        await service.load()
    return container
