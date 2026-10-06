"""tenancy.py: budget reservation/reconciliation and the sliding-window rate
limit, exercised directly against fakeredis rather than through the HTTP
API - these are the two Lua scripts a race condition would hide from a
single-threaded test, so each is also checked for not over-admitting when
called back-to-back at the boundary.
"""

from __future__ import annotations

import json

import fakeredis
import pytest

from app.tenancy import Tenant, TenantStore, load_tenants


@pytest.fixture
def redis():
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def tenant():
    return Tenant(
        key_hash="abc123",
        name="tenant-a",
        rate_limit_per_minute=3,
        token_budget=100,
    )


async def test_reserve_budget_succeeds_under_budget(redis, tenant):
    store = TenantStore(redis)
    assert await store.reserve_budget(tenant, 50) is True
    assert await store.budget_used(tenant) == 50


async def test_reserve_budget_fails_over_budget_and_rolls_back(redis, tenant):
    store = TenantStore(redis)
    assert await store.reserve_budget(tenant, 60) is True
    assert await store.reserve_budget(tenant, 60) is False
    # the failed reservation must not have left a partial increment behind
    assert await store.budget_used(tenant) == 60


async def test_reserve_budget_allows_exactly_at_the_ceiling(redis, tenant):
    store = TenantStore(redis)
    assert await store.reserve_budget(tenant, 100) is True


async def test_adjust_budget_can_reduce_usage_after_overestimating(redis, tenant):
    store = TenantStore(redis)
    await store.reserve_budget(tenant, 50)
    await store.adjust_budget(tenant, -20)  # actual usage was lower
    assert await store.budget_used(tenant) == 30


async def test_reserve_sets_a_ttl_even_if_adjust_recreated_the_key_untimed(
    redis, tenant
):
    # Simulates the key expiring entirely, then adjust_budget's INCRBY
    # bringing it back with no expiry - its own bug class, fixed by
    # reserve_budget checking TTL on every call rather than only on what
    # it thinks is the first write.
    key = f"budget:{tenant.key_hash}"
    await redis.delete(key)
    store = TenantStore(redis)
    await store.adjust_budget(tenant, 5)
    assert await redis.ttl(key) == -1  # no expiry yet

    await store.reserve_budget(tenant, 1)
    assert await redis.ttl(key) > 0


async def test_rate_limit_allows_up_to_the_limit(redis, tenant):
    store = TenantStore(redis)
    for _ in range(tenant.rate_limit_per_minute):
        assert await store.check_rate_limit(tenant) is True


async def test_rate_limit_rejects_once_over(redis, tenant):
    store = TenantStore(redis)
    for _ in range(tenant.rate_limit_per_minute):
        await store.check_rate_limit(tenant)
    assert await store.check_rate_limit(tenant) is False


def test_load_tenants_parses_json(monkeypatch):
    from app import tenancy

    monkeypatch.setattr(
        tenancy.settings,
        "tenants",
        json.dumps(
            {"hash1": {"name": "acme", "rate_limit_per_minute": 5, "token_budget": 10}}
        ),
    )
    tenants = load_tenants()
    assert tenants["hash1"].name == "acme"
    assert tenants["hash1"].rate_limit_per_minute == 5


def test_load_tenants_empty_string_yields_no_tenants(monkeypatch):
    from app import tenancy

    monkeypatch.setattr(tenancy.settings, "tenants", "")
    assert load_tenants() == {}
