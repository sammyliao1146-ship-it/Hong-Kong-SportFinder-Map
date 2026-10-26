from pydantic import BaseModel, Field

from backend.app.models.venue import Venue


class BookingSlot(BaseModel):
    date: str
    start: str
    end: str
    remaining: int | None = Field(default=None, ge=0)
    location: str
    facility: str


class BookingLocation(Venue):
    longitude: float | None = None
    latitude: float | None = None


class BookingVenue(BaseModel):
    venue: BookingLocation
    slots: list[BookingSlot]


class BookingCollection(BaseModel):
    sport: str
    sport_label: str = ""
    status: str
    fetched_at: str | None = None
    source_updated_at: str | None = None
    source_url: str
    dates: list[str] = Field(default_factory=list)
    venues: list[BookingVenue] = Field(default_factory=list)
    message: str = ""
