"""Official LCSD venue photos: catalog and WebP thumbnails are cached in Redis."""
import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.models.venue import Venue
from backend.app.utils.photos import (
    MAX_DOWNLOAD_BYTES, PHOTO_FEEDS, district_key, is_allowed_photo_url, name_key,
    photo_urls, quality_rank, render_thumbnail,
)

logger = logging.getLogger(__name__)
QUALITY_MANIFEST = Path(__file__).resolve().parents[1] / "data/venue_photo_quality.json"
REFRESH_SECONDS = 3600
THUMBNAIL_TTL_SECONDS = 7 * 24 * 3600
CATALOG_KEY = "photos:catalog"


class PhotoUnavailable(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class PhotoService:
    def __init__(self, cache: RedisCache, client: httpx.AsyncClient, quality_path: Path = QUALITY_MANIFEST):
        self.cache = cache
        self.client = client
        self.datasets: dict[str, list[dict]] = {}
        self.checked_at: dict[str, float] = {}
        self.photo_quality: dict[str, dict] = {}
        self.lock = asyncio.Lock()
        self._load_quality(quality_path)

    def _load_quality(self, path: Path) -> None:
        try:
            photos = json.loads(path.read_text()).get("photos", {})
            if not isinstance(photos, dict):
                raise TypeError("Invalid venue-photo quality manifest")
            self.photo_quality = photos
        except (OSError, ValueError, TypeError):
            self.photo_quality = {}

    async def load(self) -> None:
        data = await self.cache.get_json(CATALOG_KEY)
        if isinstance(data, dict):
            self.datasets = data.get("datasets", {})
            self.checked_at = data.get("checked_at", {})

    async def refresh(self) -> None:
        now = time.time()
        changed = False
        for key, url in PHOTO_FEEDS.items():
            if now - float(self.checked_at.get(key, 0)) < REFRESH_SECONDS:
                continue
            self.checked_at[key] = now
            try:
                response = await self.client.get(url, follow_redirects=True)
                response.raise_for_status()
                records = response.json()
                if not isinstance(records, list):
                    raise ValueError("Invalid LCSD photo catalog")
                self.datasets[key] = [record for record in records if isinstance(record, dict)]
                changed = True
            except (httpx.HTTPError, ValueError):
                logger.warning("Could not refresh LCSD venue-photo catalog: %s", key, exc_info=True)
        if changed:
            await self.cache.set_json(CATALOG_KEY, {"datasets": self.datasets, "checked_at": self.checked_at})

    async def enrich(self, venues: list[Venue]) -> list[Venue]:
        async with self.lock:
            await self.refresh()
            photos_by_name: dict[tuple[str, str], list[str]] = {}
            for records in self.datasets.values():
                for record in records:
                    photos = photo_urls(record)
                    if not photos:
                        continue
                    district = district_key(record.get("District_en") or record.get("District_cn"))
                    for name in (record.get("Name_en"), record.get("Name_cn")):
                        key = (name_key(name), district)
                        if key[0]:
                            existing = photos_by_name.setdefault(key, [])
                            existing.extend(url for url in photos if url not in existing)
            results = []
            for venue in venues:
                keys = [(name_key(name), district_key(venue.district)) for name in (venue.name_en, venue.name_zh) if name]
                photos = []
                for key in keys:
                    photos.extend(url for url in photos_by_name.get(key, []) if url not in photos)
                photos = [url for url in photos if self.photo_quality.get(url, {}).get("available") is not False]
                photos.sort(key=lambda url: quality_rank(self.photo_quality.get(url)), reverse=True)
                results.append(venue.model_copy(update={"photos": photos[:2]}))
            return results

    async def thumbnail(self, url: str) -> bytes:
        if not is_allowed_photo_url(url):
            raise PhotoUnavailable(400, "只允许读取康文署公开图片。")
        key = f"photos:thumb:{hashlib.sha256(url.encode()).hexdigest()}"
        cached = await self.cache.get_bytes(key)
        if cached:
            return cached
        try:
            response = await self.client.get(url, follow_redirects=False)
            if response.is_redirect:
                target = urljoin(url, response.headers.get("location", ""))
                if not is_allowed_photo_url(target):
                    raise PhotoUnavailable(404, "康文署图片不可用。")
                response = await self.client.get(target, follow_redirects=False)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PhotoUnavailable(404, "康文署图片暂时不可用。") from exc
        if len(response.content) > MAX_DOWNLOAD_BYTES or not response.headers.get("content-type", "").lower().startswith("image/"):
            raise PhotoUnavailable(415, "图片格式不受支持。")
        try:
            output = await asyncio.to_thread(render_thumbnail, response.content)
        except ValueError as exc:
            raise PhotoUnavailable(415, "图片格式不受支持或分辨率过大。") from exc
        await self.cache.set_bytes(key, output, THUMBNAIL_TTL_SECONDS)
        return output
