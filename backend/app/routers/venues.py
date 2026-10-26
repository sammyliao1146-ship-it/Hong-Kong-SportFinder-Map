from fastapi import APIRouter, Depends, HTTPException, Query, Response

from backend.app.config.container import Container
from backend.app.config.dependencies import get_container
from backend.app.models.venue import VenueCollection
from backend.app.services.photo_service import PhotoUnavailable

router = APIRouter(tags=["venues"])


@router.get("/sources")
async def sources(container: Container = Depends(get_container)) -> dict:
    return container.venues.data_status()


@router.get("/venues", response_model=VenueCollection)
async def venues(container: Container = Depends(get_container)) -> VenueCollection:
    return await container.venues.list_venues()


@router.get("/venue-photo")
async def venue_photo(url: str = Query(max_length=2048), container: Container = Depends(get_container)) -> Response:
    try:
        body = await container.photos.thumbnail(url)
    except PhotoUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return Response(body, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800"})
