"""Fold raw CSDI layers into the categories shown on the map."""
from backend.app.data.sources import BALL_SOURCE_KEYS, SOURCES
from backend.app.models.venue import Venue

# Ball facilities are recorded in their own layers but physically sit inside these hosts.
HOST_CATEGORIES = ("sports_centres", "sports_grounds", "parks_rec")


def _key(name: str) -> str:
    return "".join(name.split())


# Same-name records further apart than this (~150 m) are different places.
NEAR = 0.0015


def _nearest(candidates: list[Venue], venue: Venue) -> Venue | None:
    near = [c for c in candidates if abs(c.latitude - venue.latitude) <= NEAR and abs(c.longitude - venue.longitude) <= NEAR]
    return near[0] if near else None


def _union(*lists: list[str]) -> list[str]:
    return list(dict.fromkeys(item for items in lists for item in items))


def compose(layers: dict[str, list[Venue]]) -> list[Venue]:
    result: list[Venue] = []
    hosts: dict[str, list[Venue]] = {}
    for category in HOST_CATEGORIES:
        for source in SOURCES:
            if source.category_key != category:
                continue
            for venue in layers.get(source.key, []):
                copy = venue.model_copy(update={"source_id": category})
                result.append(copy)
                if source.key not in {"walking_tracks"}:
                    hosts.setdefault(_key(venue.name_zh), []).append(copy)
    for source in SOURCES:
        if source.category_key in HOST_CATEGORIES or source.key in BALL_SOURCE_KEYS:
            continue
        result.extend(v.model_copy(update={"source_id": source.category_key}) for v in layers.get(source.key, []))

    standalone: dict[str, list[Venue]] = {}
    for source in SOURCES:
        if source.key not in BALL_SOURCE_KEYS:
            continue
        for venue in layers.get(source.key, []):
            key = _key(venue.name_zh)
            host = _nearest(hosts.get(key, []), venue)
            if host:
                host.sports = _union(host.sports, venue.sports)
                continue
            group = standalone.setdefault(key, [])
            current = _nearest(group, venue)
            if current is None:
                suffix = f":{len(group) + 1}" if group else ""
                group.append(venue.model_copy(update={"id": f"ball_venues:{key}{suffix}", "source_id": "ball_venues", "sports": list(venue.sports)}))
            else:
                current.sports = _union(current.sports, venue.sports)
                for field in ("name_en", "address_zh", "address_en", "district", "opening_hours", "telephone", "website"):
                    if getattr(current, field) is None:
                        setattr(current, field, getattr(venue, field))
    result.extend(v for group in standalone.values() for v in group)
    return _dedupe(result)


def _dedupe(venues: list[Venue]) -> list[Venue]:
    """Collapse records that share category, name and position (e.g. several track sections of one park)."""
    seen: dict[tuple, Venue] = {}
    for venue in venues:
        key = (venue.source_id, _key(venue.name_zh), round(venue.latitude, 4), round(venue.longitude, 4))
        if (first := seen.get(key)) is None:
            seen[key] = venue
        else:
            first.sports = _union(first.sports, venue.sports)
    return list(seen.values())
