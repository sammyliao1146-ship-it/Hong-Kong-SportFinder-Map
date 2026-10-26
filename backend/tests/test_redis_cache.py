import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from backend.app.cache.redis_cache import RedisCache


def test_json_roundtrip_and_prefix():
    async def run():
        client = FakeAsyncRedis()
        cache = RedisCache(client, "t")
        await cache.set_json("k", {"a": 1})
        assert await cache.get_json("k") == {"a": 1}
        assert await client.get("t:k") is not None
        assert await cache.get_json("missing") is None
    asyncio.run(run())


def test_set_if_absent_and_rate_window():
    async def run():
        cache = RedisCache(FakeAsyncRedis(), "t")
        assert await cache.set_if_absent("lock", 30) is True
        assert await cache.set_if_absent("lock", 30) is False
        assert [await cache.hit("r", 60) for _ in range(3)] == [1, 2, 3]
    asyncio.run(run())


def test_unreachable_redis_falls_back_to_memory():
    from redis.asyncio import Redis

    async def run():
        cache = RedisCache(Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2))
        await cache.set_json("k", [1])
        assert await cache.get_json("k") == [1]
        assert await cache.set_if_absent("x", 10) is True
        assert await cache.set_if_absent("x", 10) is False
    asyncio.run(run())
