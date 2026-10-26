import asyncio
from types import SimpleNamespace

import pytest

from agent.data_access import SportsDataAccess
from agent.tools.sports_data import make_sports_tools
from backend.app.models.booking import BookingCollection, BookingSlot, BookingVenue
from backend.app.models.programme import Programme, ProgrammePage
from backend.app.models.venue import Venue, VenueCollection


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def access():
    venue = Venue(id="test-venue", source_id="sports_centres", source_record_id="1",
                  name_zh="沙田測試體育館", district="沙田區", sports=["羽毛球場"],
                  latitude=22.3, longitude=114.1)
    slots = [BookingSlot(date="2026-10-23", start="10:00", end="11:00",
                         remaining=None, location="主場", facility="羽毛球場")]

    async def get_booking(sport):
        return BookingCollection(sport=sport, status="stale", fetched_at="2026-10-23T01:00:00Z",
                                 source_url="https://example.test/official", dates=["2026-10-23"],
                                 venues=[BookingVenue(venue=venue.model_dump(), slots=slots)])

    async def list_venues():
        return VenueCollection(data_status="partial", items=[venue],
                               updated_at="2026-10-23T00:00:00Z", source_errors=["parks"])
    return SportsDataAccess(
        venues=SimpleNamespace(list_venues=list_venues),
        bookings=SimpleNamespace(get=get_booking), programmes=SimpleNamespace())


def test_venue_results_keep_partial_status_and_stable_id(access):
    result = run(access.search_venues(district="沙田", sport="羽毛球"))
    assert result["status"] == "partial"
    assert result["items"][0]["id"] == "test-venue"
    assert result["source_errors"] == ["parks"]
    assert run(access.venue_details("missing"))["venue"] is None


def test_missing_remaining_is_not_zero_and_stale_is_preserved(access):
    result = run(access.availability("badminton", "2026-10-23"))
    assert result["status"] == "stale"
    assert result["venues"][0]["slots"][0]["remaining"] is None
    outside = run(access.availability("badminton", "2026-10-24"))
    assert outside["date_in_published_range"] is False
    assert outside["venues"][0]["slots"] == []


def test_unsupported_sport_never_fetches_or_invents_capacity(access):
    async def boom(_):
        pytest.fail("must not fetch")
    access.bookings = SimpleNamespace(get=boom)
    result = run(access.availability("not-a-public-feed", "2026-10-23"))
    assert result["status"] == "unsupported"
    assert result["remaining"] is None


def test_invalid_arguments_are_bounded(access):
    with pytest.raises(ValueError):
        run(access.search_venues(limit=10000))
    with pytest.raises(ValueError):
        run(access.availability("badminton", "tomorrow"))


def test_sdk_tool_schemas_are_read_only_queries(access):
    tools = make_sports_tools(access)
    assert {t.name for t in tools} == {"get_sports_catalog", "search_sports_venues", "get_sports_venue",
        "get_booking_availability", "search_sports_programmes", "get_sports_programme",
        "recommend_sports_programmes", "find_next_sports_sessions", "prepare_sports_booking"}
    for tool in tools:
        assert tool.params_json_schema["additionalProperties"] is False


def test_capabilities_lists_only_allowed_tools(make_app):
    from fastapi.testclient import TestClient
    with TestClient(make_app()) as client:
        response = client.get("/api/v1/assistant/capabilities")
    assert response.status_code == 200
    assert response.json()["read_only"] is True
    assert len(response.json()["tools"]) == 9


def test_programme_details_preserves_missing_quota_and_notes(access):
    item = Programme(activity_no="123", name_zh="測試羽毛球班", sport="羽毛球",
                     notes_zh=["請自備球拍"], places_left=None)

    async def detail(_):
        return ProgrammePage(status="stale", items=[item], total=1, fetched_at="2026-10-23T00:00:00Z")
    access.programmes = SimpleNamespace(detail=detail)
    result = run(access.programme_details("123"))
    assert result["status"] == "stale"
    assert result["programme"]["places_left"] is None
    assert result["programme"]["notes_zh"] == ["請自備球拍"]
