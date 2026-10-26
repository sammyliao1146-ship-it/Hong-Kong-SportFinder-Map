from fastapi import APIRouter, Depends, Query

from backend.app.config.container import Container
from backend.app.config.dependencies import get_container
from backend.app.data.programme_catalog import PAGE_SIZE
from backend.app.models.programme import ProgrammeCatalog, ProgrammePage

router = APIRouter(tags=["programmes"])


@router.get("/programmes/catalog", response_model=ProgrammeCatalog)
async def catalog(container: Container = Depends(get_container)) -> ProgrammeCatalog:
    return await container.programmes.catalog()


@router.get("/programmes", response_model=ProgrammePage)
async def programmes(sport: str | None = None, district: str | None = None,
                     q: str | None = Query(default=None, max_length=100),
                     page: int = Query(default=1, ge=1),
                     page_size: int = Query(default=PAGE_SIZE, ge=1, le=100),
                     container: Container = Depends(get_container)) -> ProgrammePage:
    return await container.programmes.page(sport, district, q, page, page_size)
