from fastapi import APIRouter, Depends, HTTPException

from backend.app.config.container import Container
from backend.app.config.dependencies import get_container
from backend.app.models.booking import BookingCollection

router = APIRouter(tags=["booking"])


@router.get("/availability/sports")
async def availability_sports(container: Container = Depends(get_container)) -> dict:
    return container.bookings.catalog


@router.get("/availability", response_model=BookingCollection)
async def availability(sport: str, container: Container = Depends(get_container)) -> BookingCollection:
    if sport not in container.bookings.sports:
        raise HTTPException(status_code=422, detail="该运动暂无已接入的官方余量接口。")
    return await container.bookings.get(sport)
