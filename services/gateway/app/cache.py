"""Per-tenant response cache.

Keyed on tenant **and** request body deliberately - without the tenant in
the key, one customer could receive another's cached answer, which for a
multi-tenant platform is a data leak, not a performance bug. Only
non-streaming requests are cached; caching an SSE stream would mean
replaying it chunk-for-chunk with the original timing, which is not worth
the complexity for a cache whose point is to save GPU time, not to simulate
a stream that already finished instantly.

A cache hit still charges the tenant's token budget for the *actual* tokens
the original request used - not zero, and not a fresh estimate. Skipping
that would let a tenant hide spend behind a cache hit, which defeats the
cost-attribution dashboard this exists to feed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from .config import settings
from .observability import cache_hits_total, cache_misses_total


def _cache_key(tenant_hash: str, body: dict[str, Any]) -> str:
    # Only the fields that affect the model's output matter; stripping
    # `stream` lets a streaming and non-streaming request with otherwise
    # identical content share a cache entry.
    material = {
        "tenant": tenant_hash,
        "model": body.get("model"),
        "messages": body.get("messages"),
        "max_tokens": body.get("max_tokens"),
        "temperature": body.get("temperature"),
        "chat_template_kwargs": body.get("chat_template_kwargs"),
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"cache:{digest}"


class ResponseCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(
        self, tenant_hash: str, body: dict[str, Any]
    ) -> dict[str, Any] | None:
        raw = await self._redis.get(_cache_key(tenant_hash, body))
        if raw is None:
            cache_misses_total.inc()
            return None
        cache_hits_total.inc()
        return json.loads(raw)

    async def set(
        self, tenant_hash: str, body: dict[str, Any], response: dict[str, Any]
    ) -> None:
        await self._redis.set(
            _cache_key(tenant_hash, body),
            json.dumps(response),
            ex=settings.response_cache_ttl_seconds,
        )
