"""Public tool signatures: no arbitrary URL, filesystem or write operations."""
from agents import function_tool

from agent.data_access import SportsDataAccess


def make_sports_queries(access: SportsDataAccess) -> list:
    """Build the read-only query coroutines bound to one data-access instance."""

    async def get_sports_catalog() -> dict:
        """Discover exact sport/category keys, programme filters, sources and Hong Kong current time. Call before choosing query filters. Availability feeds are not the complete list of bookable sports."""
        return await access.catalog()

    async def search_sports_venues(query: str = "", district: str = "", sport: str = "", category: str = "", limit: int = 10) -> dict:
        """Search public venue names/addresses and facilities. Use Traditional Chinese sport/district text from catalog; category is an exact key. limit is 1–30. No distance or travel time is calculated."""
        return await access.search_venues(query, district, sport, category, limit)

    async def get_sports_venue(venue_id: str) -> dict:
        """Read address, coordinates, facilities and supplied government URL for an exact venue ID returned by search. A missing website is unknown; never invent URLs."""
        return await access.venue_details(venue_id)

    async def get_booking_availability(sport: str, on_date: str, district: str = "", venue_query: str = "", limit: int = 10) -> dict:
        """Query official public booking snapshot for an exact sport key and YYYY-MM-DD Hong Kong date. limit is 1–30 venues. Missing sport, date, slot or remaining means unknown, never full. Inspect status and timestamps before recommending."""
        return await access.availability(sport, on_date, district, venue_query, limit)

    async def search_sports_programmes(query: str = "", sport: str = "", district: str = "", page: int = 1, limit: int = 10) -> dict:
        """Find ongoing/upcoming public courses and activities. sport/district are exact catalogue labels. Positive page; limit 1–30. places_left is programme enrolment quota, not court availability."""
        return await access.search_programmes(query, sport, district, page, limit)

    async def get_sports_programme(activity_no: str) -> dict:
        """Read full dates, enrolment windows, public remaining quota, notes and official SmartPLAY URL for a returned activity number. Missing programme or quota is unknown."""
        return await access.programme_details(activity_no)

    async def recommend_sports_programmes(sport: str = "", district: str = "", query: str = "", target_query: str = "", max_fee: float | None = None, starts_on_or_after: str = "", starts_on_or_before: str = "", start_time: str = "", end_time: str = "", weekdays: list[int] | None = None, only_with_places: bool = True, limit: int = 5) -> dict:
        """Pick courses by exact catalogue sport, district, title/level keyword, participant-text keyword, whole-course fee ceiling, inclusive course-start date range and daily HH:MM window. ISO weekdays 1=Mon..7=Sun: all published class weekdays must fit. Unknown weekday prose is excluded. Fee is NOT monthly; age/level eligibility is not certified. limit 1–30."""
        from agent.selection import select_programmes
        return await select_programmes(access, sport, district, query, target_query, max_fee, starts_on_or_after, starts_on_or_before, start_time, end_time, weekdays, only_with_places, limit)

    async def find_next_sports_sessions(sport: str, from_date: str = "", to_date: str = "", start_time: str = "", end_time: str = "", district: str = "", venue_query: str = "", min_remaining: int = 1, limit: int = 5) -> dict:
        """Find earliest future published intervals with positive remaining, sorted by time in Hong Kong, NOT distance. Optional inclusive YYYY-MM-DD range, entire-slot daily HH:MM window. min_remaining counts courts/units, NOT people. No guarantee adjacent intervals use the same court. limit 1–30."""
        from agent.selection import select_sessions
        return await select_sessions(access, sport, from_date, to_date, start_time, end_time, district, venue_query, min_remaining, limit)

    async def prepare_sports_booking(sport: str, on_date: str, start_time: str, end_time: str, venue_query: str, district: str = "", limit: int = 5) -> dict:
        """Check an EXACT published date/start/end interval at a named venue and prepare a SmartPLAY SEARCH link. Never reserves, logs in or pays. YYYY-MM-DD / HH:MM Hong Kong. Empty venue_query is invalid. Link cannot select an exact facility or time. User must finish booking in SmartPLAY. Adjacent intervals cannot be merged into a confirmed continuous booking."""
        from agent.selection import select_sessions
        if not venue_query.strip():
            raise ValueError("venue_query is required; first find and choose a venue")
        return await select_sessions(access, sport, on_date, on_date, start_time, end_time, district, venue_query, 1, limit, exact=True)

    return [get_sports_catalog, search_sports_venues, get_sports_venue,
            get_booking_availability, search_sports_programmes, get_sports_programme,
            recommend_sports_programmes, find_next_sports_sessions, prepare_sports_booking]


def make_sports_tools(access: SportsDataAccess) -> list:
    return [function_tool(query) for query in make_sports_queries(access)]
