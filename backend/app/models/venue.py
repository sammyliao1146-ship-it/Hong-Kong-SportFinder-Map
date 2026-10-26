from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AvailabilityStatus(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Venue(BaseModel):
    id: str
    source_id: str
    source_record_id: str
    name_zh: str
    name_en: str | None = None
    address_zh: str | None = None
    address_en: str | None = None
    opening_hours: str | None = None
    telephone: str | None = None
    website: str | None = None
    district: str | None = None
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    sports: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    court_count: int | None = Field(default=None, ge=0)
    point_is_entrance: bool = False


class Availability(BaseModel):
    status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    remaining: int | None = Field(default=None, ge=0)
    reason: str = "no_published_data"
    observed_at: str | None = None


class VenueCollection(BaseModel):
    data_status: Literal["not_synced", "ready", "partial", "error"] = "not_synced"
    items: list[Venue] = Field(default_factory=list)
    total: int | None = None
    updated_at: str | None = None
    source_errors: list[str] = Field(default_factory=list)
    skipped_records: int = 0
    message: str = "设施数据尚未同步，当前空列表不代表没有场所。"
