from pydantic import BaseModel, Field

from backend.app.data.programme_catalog import DATASET_URL, PAGE_SIZE, SOURCE_URL, UPDATE_INTERVAL_SECONDS


class Programme(BaseModel):
    activity_no: str
    name_zh: str
    name_en: str | None = None
    sport: str
    district_zh: str | None = None
    district_en: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    days_zh: str | None = None
    days_en: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    venue_zh: str | None = None
    venue_en: str | None = None
    target_zh: str | None = None
    target_en: str | None = None
    fee: float | None = Field(default=None, ge=0)
    quota: int | None = Field(default=None, ge=0)
    places_left: int | None = Field(default=None, ge=0)
    enrol_method: str | None = None
    enrol_start_date: str | None = None
    enrol_end_date: str | None = None
    open_enrol_start_date: str | None = None
    open_enrol_end_date: str | None = None
    ballot_start_date: str | None = None
    ballot_end_date: str | None = None
    url: str | None = None
    notes_zh: list[str] = Field(default_factory=list)
    notes_en: list[str] = Field(default_factory=list)


class SportCount(BaseModel):
    key: str
    label: str
    count: int


class ProgrammeCatalog(BaseModel):
    status: str
    fetched_at: str | None = None
    source_updated_at: str | None = None
    total: int = 0
    sports: list[SportCount] = Field(default_factory=list)
    districts: list[str] = Field(default_factory=list)
    source_url: str = SOURCE_URL
    dataset_url: str = DATASET_URL
    update_interval_seconds: int = UPDATE_INTERVAL_SECONDS
    message: str = ""


class ProgrammePage(BaseModel):
    status: str
    fetched_at: str | None = None
    source_updated_at: str | None = None
    sport: str | None = None
    district: str | None = None
    total: int = 0
    page: int = 1
    page_size: int = PAGE_SIZE
    items: list[Programme] = Field(default_factory=list)
    source_url: str = SOURCE_URL
    dataset_url: str = DATASET_URL
    message: str = ""
