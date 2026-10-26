import asyncio
import json

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.models.venue import Venue
from backend.app.services.photo_service import PhotoService
from backend.app.utils.photos import photo_urls


def test_enrichment_prefers_clearer_photo_three_and_skips_dead_links(tmp_path):
    record = {
        "Name_en": "Aberdeen Tennis and Squash Centre",
        "Name_cn": "香港仔網球及壁球中心",
        "District_en": "Southern",
        "District_cn": "南區",
        "Photo_1": "small.jpg",
        "Photo_2": "missing.jpg",
        "Photo_3": "clear.jpg",
    }
    urls = photo_urls(record)
    quality_path = tmp_path / "quality.json"
    quality_path.write_text(json.dumps({"photos": {
        urls[0]: {"available": True, "width": 151, "height": 99, "sharpness": 6000},
        urls[1]: {"available": False, "reason": "404"},
        urls[2]: {"available": True, "width": 800, "height": 600, "sharpness": 2800},
    }}))

    service = PhotoService(RedisCache(None), httpx.AsyncClient(), quality_path)
    service.datasets = {"sports_centres": [record]}
    service.checked_at = {key: float("inf") for key in ("sports_centres",)}

    async def no_refresh():
        return None
    service.refresh = no_refresh
    venue = Venue(
        id="test-centre", source_id="sports_centres", source_record_id="1",
        name_zh="香港仔網球及壁球中心", name_en="Aberdeen Tennis and Squash Centre",
        district="Southern", longitude=114.16, latitude=22.25,
    )

    enriched = asyncio.run(service.enrich([venue]))[0]

    assert enriched.photos == [urls[2], urls[0]]
