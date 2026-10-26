"""Async cache backed by Redis, with an in-process fallback when Redis is unreachable."""
import json
import logging
import time
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float | None, bytes]] = {}

    async def get(self, key: str) -> bytes | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires, value = entry
        if expires is not None and expires <= time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        self._data[key] = (time.monotonic() + ttl if ttl else None, value)

    async def set_if_absent(self, key: str, ttl: int) -> bool:
        if await self.get(key) is not None:
            return False
        await self.set(key, b"1", ttl)
        return True

    async def incr_window(self, key: str, window: int) -> int:
        current = await self.get(key)
        count = int(current or 0) + 1
        entry = self._data.get(key)
        expires = entry[0] if entry and current is not None else time.monotonic() + window
        self._data[key] = (expires, str(count).encode())
        return count

    async def aclose(self) -> None:
        self._data.clear()


class RedisCache:
    """Namespaced JSON/bytes cache. A Redis outage degrades to memory instead of failing requests."""

    def __init__(self, client: Redis | None, prefix: str = "hksf") -> None:
        self.client = client
        self.prefix = prefix
        self.fallback = MemoryCache()
        self._warned = False

    @classmethod
    def from_url(cls, url: str, prefix: str = "hksf") -> "RedisCache":
        return cls(Redis.from_url(url, socket_connect_timeout=2, socket_timeout=5), prefix)

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def _degraded(self, exc: Exception) -> None:
        if not self._warned:
            logger.warning("Redis unavailable, using in-process cache: %s", exc)
            self._warned = True

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            return bool(await self.client.ping())
        except (RedisError, OSError):
            return False

    async def get_bytes(self, key: str) -> bytes | None:
        if self.client is not None:
            try:
                return await self.client.get(self._key(key))
            except (RedisError, OSError) as exc:
                self._degraded(exc)
        return await self.fallback.get(self._key(key))

    async def set_bytes(self, key: str, value: bytes, ttl: int | None = None) -> None:
        if self.client is not None:
            try:
                await self.client.set(self._key(key), value, ex=ttl)
                return
            except (RedisError, OSError) as exc:
                self._degraded(exc)
        await self.fallback.set(self._key(key), value, ttl)

    async def get_json(self, key: str) -> Any | None:
        raw = await self.get_bytes(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self.set_bytes(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(), ttl)

    async def set_if_absent(self, key: str, ttl: int) -> bool:
        """True when the caller won the right to act; used to throttle upstream retries."""
        if self.client is not None:
            try:
                return bool(await self.client.set(self._key(key), b"1", ex=ttl, nx=True))
            except (RedisError, OSError) as exc:
                self._degraded(exc)
        return await self.fallback.set_if_absent(self._key(key), ttl)

    async def hit(self, key: str, window: int) -> int:
        """Fixed-window counter, returns the number of hits in the current window."""
        if self.client is not None:
            try:
                name = self._key(key)
                count = await self.client.incr(name)
                if count == 1:
                    await self.client.expire(name, window)
                return int(count)
            except (RedisError, OSError) as exc:
                self._degraded(exc)
        return await self.fallback.incr_window(self._key(key), window)

    async def aclose(self) -> None:
        if self.client is not None:
            try:
                await self.client.aclose()
            except (RedisError, OSError):
                pass
        await self.fallback.aclose()
