"""Bounded, read-only queries shared by SDK tools and the MCP server."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.app.data.booking_catalog import SOURCE_CATALOG, SPORTS
from backend.app.data.programme_catalog import DATASET_URL
from backend.app.data.sources import CATEGORIES


class SportsDataAccess:
    def __init__(self, venues, bookings, programmes):
        self.venues = venues
        self.bookings = bookings
        self.programmes = programmes

    @staticmethod
    def _limit(limit):
        if not 1 <= limit <= 30:
            raise ValueError("limit must be between 1 and 30")

    @staticmethod
    def _contains(value, query):
        return not query or query.strip().casefold().removesuffix("區") in (value or "").casefold()

    @staticmethod
    def _venue(item):
        return item.model_dump(mode="json", exclude={"photos"})

    async def catalog(self):
        return {
            "current_time_hk": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
            "facility_categories": [{"key": c.key, "label": c.name_zh} for c in CATEGORIES],
            "booking_catalog": SOURCE_CATALOG,
            "programme_catalog": (await self.programmes.catalog()).model_dump(mode="json"),
            "facility_sources": self.venues.data_status()["sources"],
            "programme_source": DATASET_URL,
            "rules": ["Only listed booking sports publish connected availability feeds.",
                      "Missing data is unknown, never zero or full.",
                      "Availability is a snapshot, not on-site occupancy or a booking guarantee.",
                      "Venue records can overlap; this is not all Hong Kong venues."],
        }

    async def search_venues(self, query="", district="", sport="", category="", limit=10):
        self._limit(limit)
        data = await self.venues.list_venues()
        items = [v for v in data.items if
                 self._contains(" ".join(filter(None, [v.name_zh, v.name_en, v.address_zh, v.address_en])), query)
                 and self._contains(v.district, district)
                 and self._contains(" ".join(v.sports), sport)
                 and (not category or v.source_id == category)]
        return {"status": data.data_status, "updated_at": data.updated_at,
                "message": data.message, "source_errors": data.source_errors,
                "matched_records": len(items), "truncated": len(items) > limit,
                "items": [self._venue(v) for v in items[:limit]]}

    async def venue_details(self, venue_id):
        data = await self.venues.list_venues()
        item = next((v for v in data.items if v.id == venue_id), None)
        return {"status": data.data_status, "updated_at": data.updated_at,
                "message": data.message, "found": item is not None,
                "venue": self._venue(item) if item else None,
                "booking_availability": "unknown; query get_booking_availability separately"}

    async def availability(self, sport, on_date, district="", venue_query="", limit=10):
        self._limit(limit)
        date.fromisoformat(on_date)
        if sport not in SPORTS:
            return {"status": "unsupported", "remaining": None,
                    "message": "余量未知：此运动没有已接入的公开余量文件。", "supported_sports": SPORTS}
        data = await self.bookings.get(sport)
        entries = [e for e in data.venues if self._contains(e.venue.district, district)
                   and self._contains(f"{e.venue.name_zh} {e.venue.name_en or ''}", venue_query)]
        return {"status": data.status, "fetched_at": data.fetched_at,
                "source_updated_at": data.source_updated_at, "source_url": data.source_url,
                "message": data.message, "sport": sport, "date": on_date,
                "date_in_published_range": on_date in data.dates,
                "published_dates": data.dates, "matched_records": len(entries),
                "truncated": len(entries) > limit,
                "venues": [{"venue": self._venue(e.venue),
                            "slots": [s.model_dump(mode="json") for s in e.slots if s.date == on_date]}
                           for e in entries[:limit]],
                "missing_slots_mean": "unknown, not full; do not infer remaining from an empty list"}

    async def search_programmes(self, query="", sport="", district="", page=1, limit=10):
        self._limit(limit)
        if page < 1:
            raise ValueError("page must be positive")
        page_data = await self.programmes.page(sport=sport or None, district=district or None,
                                               query=query or None, page=page, page_size=limit)
        return page_data.model_dump(mode="json")

    async def programme_details(self, activity_no):
        # Use the same public search/cache lifecycle; never access private booking APIs.
        result = await self.programmes.detail(activity_no)
        item = result.items[0] if result.items else None
        return {"status": result.status, "fetched_at": result.fetched_at,
                "source_url": result.source_url, "source_updated_at": result.source_updated_at, "message": result.message,
                "found": item is not None,
                "programme": item.model_dump(mode="json") if item else None}
