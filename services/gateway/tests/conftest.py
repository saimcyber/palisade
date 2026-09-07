"""Shared test fixtures.

Env vars must be set before app.config.settings is constructed (it loads at
import time), so this module sets them at collection time, before any test
module imports app.main.
"""

from __future__ import annotations

import hashlib
import os

TEST_API_KEY = "test-key-123"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()

os.environ["PALISADE_API_KEY_HASHES"] = TEST_API_KEY_HASH
os.environ["PALISADE_UPSTREAM_BASE_URL"] = "http://upstream.test"
os.environ["PALISADE_MAX_TOKENS_CEILING"] = "512"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
def app_instance():
    return create_app()


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_API_KEY}"}
