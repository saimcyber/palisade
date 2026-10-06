"""Per-tenant identity, rate limiting and token budgets - all backed by Redis.

Static tenant facts (name, rate limit, token budget) come from
`PALISADE_TENANTS` - a JSON object keyed by API key hash, populated from a
SOPS-encrypted secret (deploy/secrets/) the same way api_key_hashes was in
M1-M3. Only the *mutable* state - request timestamps for the sliding-window
rate limit, and tokens consumed within the current budget window - lives in
Redis, because that is the part that has to survive gateway restarts and be
shared across replicas. See docs/adr/0021-tenant-store-split.md for why the
split is here rather than moving tenant identity into Redis too.

Token budgets are a rolling window (TTL on the usage counter), not a
lifetime cap - a real operator wants "N tokens per day", not "N tokens ever".
The window length is runtime behaviour (a TTL), which the project's
no-time-references rule explicitly exempts.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from redis.asyncio import Redis

from .config import settings

# Atomically reserve `estimate` tokens against the tenant's budget. Rolls
# back and returns 0 if that would exceed the budget; otherwise commits the
# reservation and returns 1. Must be a single script - a plain
# INCRBY-then-check from Python has a race between two concurrent requests
# that both read "under budget" before either writes.
#
# The TTL check (not "only on the very first write") matters:
# adjust_budget's INCRBY can recreate this key with no expiry at all if it
# ever expires between a reservation and its reconciliation - checking
# TTL < 0 on every reservation catches that case too, not just a brand-new
# key, so a tenant's window always ends up with an expiry.
_RESERVE_SCRIPT = """
local used = redis.call('INCRBY', KEYS[1], ARGV[1])
if redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[3])
end
local budget = tonumber(ARGV[2])
if used > budget then
    redis.call('DECRBY', KEYS[1], ARGV[1])
    return 0
end
return 1
"""

# Sliding-window rate limit via a sorted set of request timestamps: trim
# anything older than the window, count what's left, and only add the new
# timestamp if that count is still under the limit - also one script, for
# the same race-condition reason as above.
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
    return 0
end
redis.call('ZADD', key, now, now .. '-' .. tostring(math.random()))
redis.call('EXPIRE', key, window)
return 1
"""


@dataclass(frozen=True)
class Tenant:
    key_hash: str
    name: str
    rate_limit_per_minute: int
    token_budget: int


class BudgetExceeded(Exception):
    pass


class RateLimited(Exception):
    pass


def load_tenants() -> dict[str, Tenant]:
    """Parses PALISADE_TENANTS; empty/unset means no tenants can authenticate."""
    raw = settings.tenants.strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    tenants: dict[str, Tenant] = {}
    for key_hash, fields in parsed.items():
        tenants[key_hash] = Tenant(
            key_hash=key_hash,
            name=fields["name"],
            rate_limit_per_minute=int(
                fields.get(
                    "rate_limit_per_minute", settings.default_rate_limit_per_minute
                )
            ),
            token_budget=int(fields.get("token_budget", settings.default_token_budget)),
        )
    return tenants


class TenantStore:
    """Wraps the Redis connection and the two Lua scripts above."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._reserve = redis.register_script(_RESERVE_SCRIPT)
        self._rate_limit = redis.register_script(_RATE_LIMIT_SCRIPT)

    async def check_rate_limit(self, tenant: Tenant) -> bool:
        """True if this request is allowed; False if the tenant is over its limit."""
        allowed = await self._rate_limit(
            keys=[f"ratelimit:{tenant.key_hash}"],
            args=[time.time(), 60, tenant.rate_limit_per_minute],
        )
        return bool(allowed)

    async def reserve_budget(self, tenant: Tenant, estimate: int) -> bool:
        """True if `estimate` tokens were reserved; False if that would exceed budget."""
        reserved = await self._reserve(
            keys=[f"budget:{tenant.key_hash}"],
            args=[estimate, tenant.token_budget, settings.budget_window_seconds],
        )
        return bool(reserved)

    async def adjust_budget(self, tenant: Tenant, delta: int) -> None:
        """Reconciles a prior reservation against actual usage (delta may be negative)."""
        if delta:
            await self._redis.incrby(f"budget:{tenant.key_hash}", delta)

    async def budget_used(self, tenant: Tenant) -> int:
        value = await self._redis.get(f"budget:{tenant.key_hash}")
        return int(value) if value is not None else 0
