"""Deterministic course/session selection; never executes a reservation."""
from datetime import date, datetime, time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

HK = ZoneInfo("Asia/Hong_Kong")
FACILITY_CODES = {"badminton": "BADC", "basketball": "BASC", "volleyball": "VOLC", "tennis": "TENC", "turf-soccer-pitch": "FOTP"}
DISTRICT_CODES = dict(zip(
    "中西 東 南 灣仔 九龍城 觀塘 深水埗 黃大仙 油尖旺 北 西貢 沙田 大埔 離島 葵青 荃灣 屯門 元朗".split(),
    "CW EN SN WCH KC KT SSP WTS YTM N SK ST TP IS KWT TW TM YL".split()))


def now_hk():
    return datetime.now(HK)


def clock(value):
    parsed = time.fromisoformat(value)
    if parsed.tzinfo is not None or parsed.second or parsed.microsecond:
        raise ValueError("Time must be local HH:MM")
    return parsed


def booking_url(sport, venue, on_date):
    from backend.app.data.booking_catalog import SPORTS
    if sport not in FACILITY_CODES:
        return "https://www.smartplay.lcsd.gov.hk/facilities/home"
    return "https://www.smartplay.lcsd.gov.hk/facilities/search-result?" + urlencode({
        "typeCode": FACILITY_CODES[sport], "typeName": SPORTS.get(sport, sport), "sportCode": "BAGM", "groupCode": "BAGM",
        "playDate": on_date, "isFree": "false", "keywords": venue.name_zh,
        "district": DISTRICT_CODES.get((venue.district or "").removesuffix("區"), "all")})


async def select_sessions(access, sport, from_date="", to_date="", start_time="", end_time="",
                          district="", venue_query="", min_remaining=1, limit=5, exact=False):
    from backend.app.data.booking_catalog import SPORTS
    access._limit(limit)
    if min_remaining < 1:
        raise ValueError("min_remaining must be positive")
    now = now_hk()
    first = date.fromisoformat(from_date) if from_date else now.date()
    last = date.fromisoformat(to_date) if to_date else None
    if last and last < first:
        raise ValueError("to_date must not precede from_date")
    start = clock(start_time) if start_time else None
    end = clock(end_time) if end_time else None
    if start and end and end <= start:
        raise ValueError("end_time must be later than start_time; overnight requests are unsupported")
    if sport not in SPORTS:
        return {"status": "unsupported", "candidates": [], "booking_completed": False,
                "message": "余量未知：此运动没有已接入的公开余量文件。"}
    data = await access.bookings.get(sport)
    candidates, unknown, zero = [], 0, 0
    for entry in data.venues:
        v = entry.venue
        if not access._contains(v.district, district) or not access._contains(f"{v.name_zh} {v.name_en or ''}", venue_query):
            continue
        for slot in entry.slots:
            day, a, b = date.fromisoformat(slot.date), clock(slot.start), clock(slot.end)
            if day < first or (last and day > last) or datetime.combine(day, a, HK) <= now:
                continue
            if (exact and (a != start or b != end)) or (not exact and ((start and a < start) or (end and b > end))):
                continue
            if slot.remaining is None:
                unknown += 1
                continue
            if slot.remaining < min_remaining:
                zero += 1
                continue
            candidates.append({"venue": access._venue(v), "slot": slot.model_dump(mode="json"),
                "booking_url": booking_url(sport, v, slot.date), "booking_link_scope": "search_results_only",
                "booking_completed": False})
    candidates.sort(key=lambda c: (c["slot"]["date"], c["slot"]["start"], c["venue"]["name_zh"], c["slot"]["end"]))
    return {"status": data.status, "fetched_at": data.fetched_at, "source_updated_at": data.source_updated_at,
            "source_url": data.source_url, "message": data.message, "published_dates": data.dates,
            "requested_date_published": first.isoformat() in data.dates if exact else None,
            "sort": "earliest_start_time_hk; not geographic distance", "matched_sessions": len(candidates),
            "truncated": len(candidates) > limit, "candidates": candidates[:limit],
            "unknown_matching_records": unknown, "insufficient_matching_records": zero,
            "booking_completed": False, "action": "complete_booking_in_smartplay",
            "limitations": ["Missing slots or dates are unknown, never full.",
                "Counts describe public snapshots, not a guaranteed reservation.",
                "Each result is one published interval; adjacent intervals do not prove the same court is available.",
                "Search links cannot lock venue/facility/time; select and verify in SmartPLAY."]}


async def select_programmes(access, sport="", district="", query="", target_query="", max_fee=None,
                            starts_on_or_after="", starts_on_or_before="", start_time="", end_time="",
                            weekdays=None, only_with_places=True, limit=5):
    access._limit(limit)
    if max_fee is not None and max_fee < 0:
        raise ValueError("max_fee must be nonnegative")
    days = set(weekdays or [])
    if not days.issubset(set(range(1, 8))):
        raise ValueError("weekdays must use ISO Monday=1 through Sunday=7")
    first = date.fromisoformat(starts_on_or_after) if starts_on_or_after else None
    last = date.fromisoformat(starts_on_or_before) if starts_on_or_before else None
    if first and last and last < first:
        raise ValueError("Invalid start date range")
    a, b = clock(start_time) if start_time else None, clock(end_time) if end_time else None
    if a and b and b <= a:
        raise ValueError("Invalid daily time window")
    data = await access.programmes.snapshot()
    items, uncertain = [], 0
    for p in data.items:
        if sport and p.sport != sport or not access._contains(p.district_zh, district):
            continue
        if not access._contains(f"{p.name_zh} {p.name_en or ''} {p.venue_zh or ''}", query):
            continue
        if not access._contains(f"{p.target_zh or ''} {p.target_en or ''}", target_query):
            continue
        if max_fee is not None and (p.fee is None or p.fee > max_fee):
            continue
        if (first or last) and (not p.start_date or (first and date.fromisoformat(p.start_date) < first) or (last and date.fromisoformat(p.start_date) > last)):
            continue
        if a and (not p.start_time or clock(p.start_time) < a) or b and (not p.end_time or clock(p.end_time) > b):
            continue
        if days:
            # The official weekday text can contain exclusions. Do not infer all class days from the first date.
            known_days = parse_weekdays(p.days_en, p.days_zh)
            if not known_days or not known_days.issubset(days):
                uncertain += int(not known_days)
                continue
        if only_with_places and (p.places_left is None or p.places_left <= 0):
            uncertain += int(p.places_left is None)
            continue
        items.append(p.model_dump(mode="json"))
    items.sort(key=lambda p: (p["start_date"] or "9999", p["start_time"] or "99:99", p["fee"] if p["fee"] is not None else float("inf"), p["activity_no"]))
    return {"status": data.status, "fetched_at": data.fetched_at, "source_url": data.source_url,
            "source_updated_at": data.source_updated_at, "matched_programmes": len(items),
            "truncated": len(items) > limit, "items": items[:limit], "excluded_unknown_records": uncertain,
            "message": "按开课日期、时间、费用排序；只匹配公开字段。名额不证明报名窗口已开放或用户符合资格。费用是该课程公布费用，不是月费。"}


def parse_weekdays(english, chinese):
    import re
    # Accept only unambiguous weekday lists; exclusion prose must remain unverified.
    en = (english or "").strip().lower()
    words = {"mon": 1, "monday": 1, "tue": 2, "tuesday": 2, "wed": 3, "wednesday": 3,
             "thu": 4, "thursday": 4, "fri": 5, "friday": 5, "sat": 6, "saturday": 6, "sun": 7, "sunday": 7}
    tokens = [x for x in re.split(r"[,/;&\s]+", en) if x]
    if tokens and all(x in words for x in tokens):
        return {words[x] for x in tokens}
    zh = (chinese or "").strip()
    tokens = [x for x in re.split(r"[,，、/;；\s]+", zh) if x]
    result = set()
    for token in tokens:
        m = re.fullmatch(r"(?:星期|週|周)([一二三四五六日天])", token)
        if not m:
            return None
        result.add("一二三四五六日".find(m[1].replace("天", "日")) + 1)
    return result or None
