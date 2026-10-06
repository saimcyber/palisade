"""Shared test fixtures.

Env vars must be set before app.config.settings is constructed (it loads at
import time), so this module sets them at collection time, before any test
module imports app.main. Redis is faked (fakeredis) rather than skipped -
tenancy.py's Lua scripts are exactly the part most likely to have a bug, so
a test suite that never exercises them would miss the race-condition fixes
they exist for.
"""

from __future__ import annotations

import hashlib
import json
import os

TEST_API_KEY = "test-key-123"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()
TEST_TENANT_NAME = "tenant-a"
TEST_RATE_LIMIT = 1000
TEST_TOKEN_BUDGET = 100_000

SECOND_API_KEY = "test-key-456"
SECOND_API_KEY_HASH = hashlib.sha256(SECOND_API_KEY.encode("utf-8")).hexdigest()
SECOND_TENANT_NAME = "tenant-b"

os.environ["PALISADE_TENANTS"] = json.dumps(
    {
        TEST_API_KEY_HASH: {
            "name": TEST_TENANT_NAME,
            "rate_limit_per_minute": TEST_RATE_LIMIT,
            "token_budget": TEST_TOKEN_BUDGET,
        },
        SECOND_API_KEY_HASH: {
            "name": SECOND_TENANT_NAME,
            "rate_limit_per_minute": TEST_RATE_LIMIT,
            "token_budget": TEST_TOKEN_BUDGET,
        },
    }
)
os.environ["PALISADE_UPSTREAM_BASE_URL"] = "http://upstream.test"
os.environ["PALISADE_MAX_TOKENS_CEILING"] = "512"
os.environ["PALISADE_REDIS_URL"] = "redis://fake"

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.main as main_module  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def fake_redis(monkeypatch):
    instance = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(main_module.Redis, "from_url", lambda *a, **k: instance)
    yield instance


@pytest.fixture
def app_instance(fake_redis):
    return create_app()


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture
def second_tenant_auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SECOND_API_KEY}"}
