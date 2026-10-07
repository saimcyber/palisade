"""loadshed.py and its wiring into chat.py: a saturated in-flight limit
sheds load with 503 rather than queueing behind work the GPU cannot
speed up (ADR 0024), and the reservation it would have burned gets
refunded since no tokens were ever generated."""

from __future__ import annotations

import respx
from httpx import Response

from app.config import settings
from app.loadshed import InFlightLimiter

NON_STREAM_BODY = {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 16}


def test_try_acquire_respects_the_limit():
    limiter = InFlightLimiter(2)
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


def test_release_frees_a_slot():
    limiter = InFlightLimiter(1)
    assert limiter.try_acquire() is True
    limiter.release()
    assert limiter.try_acquire() is True


@respx.mock
def test_saturated_limiter_sheds_load_with_503(client, auth_headers):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "1",
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    # Exhaust the limiter directly rather than racing real concurrent
    # requests - simpler and deterministic.
    for _ in range(settings.max_in_flight_upstream_requests):
        client.app.state.in_flight_limiter.try_acquire()

    response = client.post(
        "/v1/chat/completions", headers=auth_headers, json=NON_STREAM_BODY
    )
    assert response.status_code == 503
    assert response.json()["error"] == "upstream_saturated"
    assert response.headers["Retry-After"] == "2"


@respx.mock
def test_shedding_refunds_the_budget_reservation(client, auth_headers):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(200, json={"id": "1", "choices": [], "usage": {}})
    )
    before = client.get("/metrics").text

    for _ in range(settings.max_in_flight_upstream_requests):
        client.app.state.in_flight_limiter.try_acquire()
    shed = client.post(
        "/v1/chat/completions", headers=auth_headers, json=NON_STREAM_BODY
    )
    assert shed.status_code == 503

    for _ in range(settings.max_in_flight_upstream_requests):
        client.app.state.in_flight_limiter.release()
    after = client.get("/metrics").text

    def _remaining(text: str) -> float:
        for line in text.splitlines():
            if line.startswith('palisade_tenant_budget_remaining{tenant="tenant-a"}'):
                return float(line.rsplit(" ", 1)[1])
        return -1.0

    # The reservation was refunded - remaining budget is unchanged by the
    # shed request (within the estimate, since nothing else ran between).
    assert _remaining(after) == _remaining(before)


@respx.mock
def test_a_freed_slot_lets_the_next_request_through(client, auth_headers):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "1",
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    )
    response = client.post(
        "/v1/chat/completions", headers=auth_headers, json=NON_STREAM_BODY
    )
    assert response.status_code == 200
    # The limiter must have released its slot after a normal request.
    assert client.app.state.in_flight_limiter.in_flight == 0
