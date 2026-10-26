import asyncio

import pytest

from backend.app.cache.redis_cache import RedisCache
from backend.app.config.container import build_container
from backend.app.config.factory import create_app
from backend.app.config.settings import Settings
from backend.app.routers import assistant, booking, health, programmes, venues

ROUTERS = [health.router, venues.router, booking.router, programmes.router, assistant.router]


def make_settings(api_key: str = "", model: str = "", **extra) -> Settings:
    return Settings(api_key, model, "", ["http://localhost:5173"], **extra)


async def _noop(*_args, **_kwargs) -> None:
    return None


@pytest.fixture
def make_app():
    """Build an app whose container uses an in-memory cache and never touches upstream services."""
    def build(settings: Settings | None = None):
        settings = settings or make_settings()
        container = asyncio.run(build_container(settings, RedisCache(None)))
        container.venues.refresh_if_due = _noop
        container.photos.refresh = _noop
        container.programmes.refresh_if_needed = _noop
        app = create_app(ROUTERS, settings)
        app.state.container = container
        return app
    return build
