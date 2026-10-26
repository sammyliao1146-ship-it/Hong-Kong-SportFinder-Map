"""Pure normalisation of SmartPLAY booking snapshots. Missing counts stay unknown, never zero."""
import hashlib
from datetime import date, datetime

from backend.app.data.booking_catalog import SPORTS
from backend.app.models.booking import BookingLocation, BookingSlot, BookingVenue
from backend.app.models.venue import Venue


def normalize_rows(rows: list[dict], sport: str, facilities: list[Venue]) -> list[BookingVenue]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty or invalid booking snapshot")
    known = {v.name_en.strip().lower(): v for v in facilities if v.name_en}
    groups = {}
    seen = {}
    for row in rows:
        name = row["Venue_Name_TC"].strip()
        district = row["District_Name_TC"].strip()
        english = row["Venue_Name_EN"].strip()
        identity = (english, district)
        raw = str(row.get("Available_Courts", "")).strip()
        remaining = int(raw) if raw.isdigit() else None
        day = date.fromisoformat(row["Available_Date"]).isoformat()
        start, end = row["Session_Start_Time"], row["Session_End_Time"]
        datetime.strptime(start, "%H:%M"); datetime.strptime(end, "%H:%M")
        slot = BookingSlot(date=day, start=start, end=end, remaining=remaining,
                           location=row["Facility_Location_Name_TC"].strip(), facility=row["Facility_Type_Name_TC"].strip())
        slot_key = (*identity, day, start, end, slot.location, slot.facility)
        if slot_key in seen:
            if seen[slot_key] != remaining:
                raise ValueError("Conflicting duplicate booking slot")
            continue
        seen[slot_key] = remaining
        if identity not in groups:
            match = known.get(english.lower())
            lon = float(row["Venue_Longitude"]) if row.get("Venue_Longitude") else match.longitude if match else None
            lat = float(row["Venue_Latitude"]) if row.get("Venue_Latitude") else match.latitude if match else None
            if lon is not None and lat is not None and not (113.8 <= lon <= 114.5 and 22.1 <= lat <= 22.6):
                raise ValueError("Invalid booking venue coordinates")
            identifier = hashlib.sha256("|".join(identity).encode()).hexdigest()[:16]
            venue = BookingLocation(id=f"booking:{sport}:{identifier}", source_id="booking", source_record_id=identifier,
                          name_zh=name, name_en=english, district=district, longitude=lon, latitude=lat,
                          address_zh=row.get("Venue_Address_TC"), address_en=row.get("Venue_Address_EN"),
                          photos=match.photos if match else [],
                          telephone=row.get("Venue_Phone_No."), sports=[SPORTS[sport]],
                          website=match.website if match else None)
            groups[identity] = BookingVenue(venue=venue, slots=[])
        groups[identity].slots.append(slot)
    for group in groups.values():
        group.slots.sort(key=lambda s: (s.date, s.start, s.end, s.location, s.facility))
    return sorted(groups.values(), key=lambda v: v.venue.name_en or v.venue.name_zh)
