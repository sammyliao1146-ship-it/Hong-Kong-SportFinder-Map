"""Application lifespan: build services on startup, warm caches, release resources on shutdown."""
import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from backend.app.config.container import Container, build_container
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)


async def _warm_up(container: Container) -> None:
    for task in (container.photos.refresh(), container.venues.refresh_if_due()):
        try:
            await task
        except Exception:
            logger.exception("Cache warm-up step failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = getattr(app.state, "container", None) or await build_container(get_settings())
    app.state.container = container
    warm = asyncio.create_task(_warm_up(container))
    try:
        yield
    finally:
        warm.cancel()
        with suppress(asyncio.CancelledError):
            await warm
        await container.aclose()
