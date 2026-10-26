"""Ten-minute cache of LCSD SmartPLAY community programmes in Redis, with stale fallback."""
import asyncio
import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from backend.app.cache.redis_cache import RedisCache
from backend.app.data.programme_catalog import PAGE_SIZE, SOURCE_URL, UPDATE_INTERVAL_SECONDS
from backend.app.models.programme import Programme, ProgrammeCatalog, ProgrammePage, SportCount
from backend.app.utils.programmes import normalize_programmes

logger = logging.getLogger(__name__)
SNAPSHOT_KEY = "programmes:snapshot"


class ProgrammeService:
    def __init__(self, cache: RedisCache, client: httpx.AsyncClient, throttle_seconds: int = 60):
        self.cache = cache
        self.client = client
        self.throttle_seconds = throttle_seconds
        self.items: list[Programme] = []
        self.fetched_at: str | None = None
        self.source_updated_at: str | None = None
        self.status = "not_synced"
        self.lock = asyncio.Lock()

    async def load(self) -> None:
        cache = await self.cache.get_json(SNAPSHOT_KEY)
        try:
            self.items = [Programme.model_validate(item) for item in cache["items"]]
            self.fetched_at = cache.get("fetched_at")
            self.source_updated_at = cache.get("source_updated_at")
            self.status = "ready" if self.items else "not_synced"
        except (ValueError, KeyError, TypeError):
            pass

    def _age(self) -> float:
        return time.time() - datetime.fromisoformat(self.fetched_at).timestamp() if self.fetched_at else float("inf")

    async def refresh_if_needed(self) -> None:
        if self._age() < UPDATE_INTERVAL_SECONDS:
            self.status = "ready"
            return
        async with self.lock:
            if self._age() < UPDATE_INTERVAL_SECONDS:
                self.status = "ready"
                return
            if self.throttle_seconds and not await self.cache.set_if_absent("programmes:attempt", self.throttle_seconds):
                self.status = "stale" if self.items else "error"
                return
            try:
                response = await self.client.get(SOURCE_URL, timeout=45, follow_redirects=True)
                response.raise_for_status()
                items = normalize_programmes(response.json())
                self.items = items
                self.fetched_at = datetime.now(timezone.utc).isoformat()
                self.source_updated_at = response.headers.get("last-modified")
                self.status = "ready"
                await self.cache.set_json(SNAPSHOT_KEY, {
                    "fetched_at": self.fetched_at, "source_updated_at": self.source_updated_at,
                    "items": [item.model_dump() for item in items]})
            except Exception:
                logger.exception("SmartPLAY programme sync failed")
                self.status = "stale" if self.items else "error"

    def _active(self) -> list[Programme]:
        today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat()
        return [item for item in self.items if not item.end_date or item.end_date >= today]

    def _message(self, ready: str) -> str:
        return (ready if self.status == "ready"
                else "正在显示旧数据，官方课程快照更新失败。" if self.status == "stale"
                else "暂时无法取得官方课程资料，请稍后重试。")

    async def catalog(self) -> ProgrammeCatalog:
        await self.refresh_if_needed()
        active = self._active()
        counts: dict[str, int] = {}
        for item in active:
            counts[item.sport] = counts.get(item.sport, 0) + 1
        sports = [SportCount(key=label, label=label, count=count)
                  for label, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].casefold()))]
        districts = sorted({item.district_zh for item in active if item.district_zh}, key=str.casefold)
        return ProgrammeCatalog(status=self.status, fetched_at=self.fetched_at,
            source_updated_at=self.source_updated_at, total=len(active), sports=sports, districts=districts,
            message=self._message("只显示仍在进行或未开始的课程；公开名额和报名资格请以康体通详情页为准。"))

    async def snapshot(self) -> ProgrammePage:
        """Internal selection snapshot; filter before returning results to the model."""
        await self.refresh_if_needed()
        items = self._active()
        return ProgrammePage(status=self.status, fetched_at=self.fetched_at,
            source_updated_at=self.source_updated_at, total=len(items), items=items,
            message=self._message("课程公开数据快照"))

    async def detail(self, activity_no: str) -> ProgrammePage:
        await self.refresh_if_needed()
        item = next((p for p in self._active() if p.activity_no == activity_no), None)
        return ProgrammePage(status=self.status, fetched_at=self.fetched_at,
            source_updated_at=self.source_updated_at, total=1 if item else 0,
            page_size=1, items=[item] if item else [],
            message="课程公开余量只是数据快照；请以康体通实际报名结果为准。")

    async def page(self, sport: str | None = None, district: str | None = None, query: str | None = None,
                   page: int = 1, page_size: int = PAGE_SIZE) -> ProgrammePage:
        await self.refresh_if_needed()
        filtered = self._active()
        if sport:
            filtered = [item for item in filtered if item.sport == sport]
        if district:
            filtered = [item for item in filtered if item.district_zh == district]
        if query:
            needle = query.casefold().strip()
            filtered = [item for item in filtered if needle in " ".join(filter(None, [item.name_zh, item.name_en, item.sport, item.venue_zh, item.venue_en, item.district_zh, item.district_en])).casefold()]
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        start = (page - 1) * page_size
        return ProgrammePage(status=self.status, fetched_at=self.fetched_at, source_updated_at=self.source_updated_at,
            sport=sport, district=district, total=len(filtered), page=page, page_size=page_size,
            items=filtered[start:start + page_size],
            message=self._message("公開名額只是資料快照；报名资格和实际报名状态以康体通详情页为准。"))
