"""CSDI ArcGIS adapters. Keep layer identities; overlapping layers are not unique venues."""
import html
import re

import httpx

from backend.app.data.sources import BALL_SOURCE_KEYS, FacilitySource
from backend.app.models.venue import Venue


def clean(value):
    if value is None:
        return None
    text = html.unescape(re.sub(r"<[^>]*>", " ", str(value))).strip()
    return None if text.lower() in {"", "n.a.", "n/a", "null", "none", "-"} else text


def normalize(source: FacilitySource, feature: dict) -> Venue:
    p = feature.get("properties") or {}
    def pick(*keys):
        return next((value for key in keys if (value := clean(p.get(key))) is not None), None)
    geometry = feature.get("geometry") or {}
    kind = geometry.get("type")
    if kind == "Point":
        lon, lat = geometry["coordinates"][:2]
    elif kind in {"LineString", "MultiLineString"}:
        # Trails are drawn as lines; mark them at the middle vertex of the first line.
        line = geometry["coordinates"][0] if kind == "MultiLineString" else geometry["coordinates"]
        lon, lat = line[len(line) // 2][:2]
    else:
        raise ValueError("Missing point geometry")
    # These are Hong Kong facility layers; reject invalid/projected coordinates.
    if not (113.8 <= lon <= 114.5 and 22.1 <= lat <= 22.6):
        raise ValueError("Coordinates outside Hong Kong")
    record_id = pick("OBJECTID") or clean(feature.get("id"))
    name = pick("NameTC", "NAME_TC", "Name_cn", "Venue_name_tc", "SITE_NAME_TC", "TRAIL_NAME_TC", "Walking_Track_TC",
                "Name_en", "NAME_EN", "NameEN", "SITE_NAME_EN", "TRAIL_NAME_EN", "Walking_Track_EN")
    if not name or not record_id:
        raise ValueError("Missing name or source identity")
    court_count = pick("No__of_Basketball_Courts_TC", "No__of_Basketball_Courts_EN")
    try:
        court_count = int(court_count) if court_count is not None else None
    except ValueError:
        court_count = None
    website = pick("WebsiteTC", "WebsiteEN", "WEBSITE")
    sports = [v.strip() for v in (pick("FacilityTypeTC", "SEARCH02_TC", "Facilities_tc", "Facilities_cn") or "").split(",") if v.strip() and not v.strip().startswith("http")]
    if source.key in BALL_SOURCE_KEYS:
        sports = [source.default_sport]
    elif source.default_sport:
        sports = [source.default_sport, *sports]
        if source.key == "sports_grounds":
            for n in range(1, 7):
                sports += [v.strip() for v in (pick(f"NSEARCH0{n}_TC") or "").split(",") if v.strip() and not v.strip().startswith("http")]
        sports += [v for v in (pick("TYPE_TC", "DIFFICULTY_TC"),) if v]
        sports = list(dict.fromkeys(sports))
    start, finish = pick("STARTpt_TC"), pick("FINISHpt_TC")
    trail_route = f"{start} → {finish}" if start and finish else None
    start_en, finish_en = pick("STARTpt_EN"), pick("FINISHpt_EN")
    trail_route_en = f"{start_en} → {finish_en}" if start_en and finish_en else None
    return Venue(
        id=f"{source.key}:{record_id}", source_id=source.key, source_record_id=record_id,
        name_zh=name, name_en=pick("NameEN", "NAME_EN", "Name_en", "Venue_name_en", "SITE_NAME_EN", "TRAIL_NAME_EN", "Walking_Track_EN"),
        address_zh=pick("AddressTC", "ADDRESS_TC", "Address_tc", "Address_cn") or trail_route or pick("COUNTRY_PARK_TC"),
        address_en=pick("AddressEN", "ADDRESS_EN", "Address_en") or trail_route_en or pick("COUNTRY_PARK_EN"),
        district=pick("DistrictTC", "SEARCH01_TC", "District_tc", "District_cn", "District_TC", "REGION_TC"),
        longitude=lon, latitude=lat,
        sports=sports,
        court_count=court_count,
        opening_hours=pick("OpeningHoursTC", "Opening_hours_tc", "Opening_hours_cn", "OpeningHoursEN"),
        telephone=pick("TelephoneTC", "Phone", "Enquiry_no", "TEL"),
        website=website if website and website.startswith(("https://", "http://")) else None,
    )


async def fetch_source(source: FacilitySource, client: httpx.AsyncClient) -> tuple[list[Venue], int]:
    records = {}
    offset = 0
    skipped = 0
    for _ in range(100):
        response = await client.get(source.query_url, params={
            "where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
            "orderByFields": "OBJECTID ASC", "resultOffset": offset, "resultRecordCount": 1000,
        })
        response.raise_for_status()
        page = response.json()
        if "error" in page or page.get("type") != "FeatureCollection":
            raise ValueError("Invalid CSDI response")
        features = page["features"]
        previous = len(records)
        for feature in features:
            try:
                venue = normalize(source, feature)
                records[venue.id] = venue
            except (ValueError, TypeError, KeyError, IndexError):
                skipped += 1
        more = page.get("exceededTransferLimit") or (page.get("properties") or {}).get("exceededTransferLimit")
        if not more:
            return list(records.values()), skipped
        if not features or len(records) == previous:
            raise ValueError("CSDI pagination did not advance")
        offset += len(features)
    raise ValueError("CSDI pagination limit exceeded")
