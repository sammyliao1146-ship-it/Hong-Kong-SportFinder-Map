"""Pure parsing of the official SmartPLAY programme snapshot."""
from datetime import date

from backend.app.data.programme_catalog import SPORT_ALIASES, TITLE_SPORTS
from backend.app.models.programme import Programme


def _text(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _notes(row: dict, key: str) -> list[str]:
    value = row.get(key)
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [text for item in values if (text := str(item).strip())]


def _int(row: dict, key: str) -> int | None:
    value = row.get(key)
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = int(float(value))
        return result if result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _float(row: dict, key: str) -> float | None:
    value = row.get(key)
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _date(row: dict, key: str) -> str | None:
    value = _text(row, key)
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def classify_sport(activity_type: str | None, name_zh: str, name_en: str | None) -> str:
    category = (activity_type or "").strip()
    if category in SPORT_ALIASES:
        return SPORT_ALIASES[category]
    for alias, label in SPORT_ALIASES.items():
        if category and alias and alias in category:
            return label
    combined = f"{name_zh} {name_en or ''}".casefold()
    for alias, label in TITLE_SPORTS:
        if alias.casefold() in combined:
            return label
    return category or "其他活動"


def normalize_programmes(rows: list[dict]) -> list[Programme]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty or invalid public programme snapshot")
    programmes = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        activity_no = _text(row, "ACTIVITY_NO")
        name_zh = _text(row, "TC_PGM_NAME")
        if not activity_no or not name_zh or activity_no in seen:
            continue
        seen.add(activity_no)
        name_en = _text(row, "EN_PGM_NAME")
        url = _text(row, "TC_URL")
        if not url or not url.startswith("https://www.smartplay.lcsd.gov.hk/"):
            url = None
        programmes.append(Programme(
            activity_no=activity_no, name_zh=name_zh, name_en=name_en,
            sport=classify_sport(_text(row, "TC_ACT_TYPE_NAME"), name_zh, name_en),
            district_zh=_text(row, "TC_DISTRICT"), district_en=_text(row, "EN_DISTRICT"),
            start_date=_date(row, "PGM_START_DATE"), end_date=_date(row, "PGM_END_DATE"),
            days_zh=_text(row, "TC_DAY"), days_en=_text(row, "EN_DAY"),
            start_time=_text(row, "PGM_START_TIME"), end_time=_text(row, "PGM_END_TIME"),
            venue_zh=_text(row, "TC_VENUE"), venue_en=_text(row, "EN_VENUE"),
            target_zh=_text(row, "TC_TARGET_GRP"), target_en=_text(row, "EN_TARGET_GRP"),
            fee=_float(row, "FEE"), quota=_int(row, "QUOTA"), places_left=_int(row, "PLACES_LEFT"),
            enrol_method=_text(row, "ENROL_METHOD"),
            enrol_start_date=_date(row, "ENROL_START_DATE"), enrol_end_date=_date(row, "ENROL_END_DATE"),
            open_enrol_start_date=_date(row, "OPEN_ENROL_START_DATE"), open_enrol_end_date=_date(row, "OPEN_ENROL_END_DATE"),
            ballot_start_date=_date(row, "BALLOT_START_DATE"), ballot_end_date=_date(row, "BALLOT_END_DATE"),
            url=url, notes_zh=_notes(row, "TC_NOTES"), notes_en=_notes(row, "EN_NOTES"),
        ))
    if not programmes:
        raise ValueError("No valid programme records in official snapshot")
    return sorted(programmes, key=lambda item: (item.start_date or "9999", item.sport.casefold(), item.name_zh.casefold()))
