"""cache.py: tenant isolation is the one property that must never regress -
a cache key collision across tenants would mean one customer's answer
served to another."""

from __future__ import annotations

import fakeredis
import pytest

from app.cache import ResponseCache


@pytest.fixture
def redis():
    return fakeredis.FakeAsyncRedis(decode_responses=True)


BODY = {"model": "palisade-small", "messages": [{"role": "user", "content": "hi"}]}


async def test_miss_then_hit(redis):
    cache = ResponseCache(redis)
    assert await cache.get("tenant-a", BODY) is None
    await cache.set("tenant-a", BODY, {"id": "1", "usage": {}})
    assert (await cache.get("tenant-a", BODY))["id"] == "1"


async def test_different_tenants_never_share_a_cache_entry(redis):
    cache = ResponseCache(redis)
    await cache.set("tenant-a", BODY, {"id": "from-a"})
    assert await cache.get("tenant-b", BODY) is None


async def test_streaming_flag_does_not_affect_the_cache_key(redis):
    cache = ResponseCache(redis)
    await cache.set("tenant-a", {**BODY, "stream": True}, {"id": "x"})
    assert (await cache.get("tenant-a", {**BODY, "stream": False}))["id"] == "x"


async def test_different_messages_are_different_cache_entries(redis):
    cache = ResponseCache(redis)
    await cache.set("tenant-a", BODY, {"id": "first"})
    other = {**BODY, "messages": [{"role": "user", "content": "bye"}]}
    assert await cache.get("tenant-a", other) is None
