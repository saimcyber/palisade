"""Found live during M5's chaos day (docs/evidence/m5/03-*): pausing
Redis caused an uncaught redis.exceptions.TimeoutError from the very
first Redis call (the rate-limit check) - a bare 500 with no audit
line and no metric. create_chat_completion's wrapper now converts any
RedisError into a clean, audited 503."""

from __future__ import annotations

import logging

import redis.exceptions

NON_STREAM_BODY = {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 16}


def test_redis_error_on_rate_limit_check_becomes_a_clean_503(
    client, auth_headers, monkeypatch, caplog
):
    import app.main as main_module

    async def _raise(self, tenant):
        raise redis.exceptions.TimeoutError("Timeout reading from redis:6379")

    monkeypatch.setattr(main_module.TenantStore, "check_rate_limit", _raise)

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/v1/chat/completions", headers=auth_headers, json=NON_STREAM_BODY
        )

    assert response.status_code == 503
    assert response.json()["error"] == "redis_unavailable"

    settled = [r for r in caplog.records if "chat_completion_settled" in r.getMessage()]
    assert settled, "no audit line was emitted for the Redis failure"
    assert settled[-1].extra_fields["outcome"] == "redis_unavailable"


def test_redis_error_mid_request_does_not_crash_the_process(
    client, auth_headers, monkeypatch
):
    """A RedisError anywhere else in the handler (not just the first
    call) must still come back as a clean response, not an unhandled
    exception reaching the ASGI layer."""
    import app.main as main_module

    async def _raise(self, tenant, estimate):
        raise redis.exceptions.ConnectionError("Connection refused")

    monkeypatch.setattr(main_module.TenantStore, "reserve_budget", _raise)

    response = client.post(
        "/v1/chat/completions", headers=auth_headers, json=NON_STREAM_BODY
    )
    assert response.status_code == 503
