"""Streaming: chunks are relayed in order, unmodified, and without buffering
the whole response first - buffering would silently turn TTFT into "time to
last token" without any single assertion catching it, so order is what a
unit test can verify; the acceptance test (M1 Verification table) is what
actually proves live incremental delivery against a real vLLM.
"""

from __future__ import annotations

import json
import logging

import httpx
import respx
from httpx import Response

SSE_BODY = (
    'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":"!"}}]}\n\n'
    "data: [DONE]\n\n"
)


@respx.mock
def test_stream_chunks_relayed_in_order(client, auth_headers):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(
            200, content=SSE_BODY, headers={"content-type": "text/event-stream"}
        )
    )

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
    ) as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]

    contents = []
    for line in lines:
        if not line.startswith("data:"):
            continue
        payload = line.removeprefix("data:").strip()
        if payload == "[DONE]":
            continue
        chunk = json.loads(payload)
        contents.append(chunk["choices"][0]["delta"]["content"])

    assert contents == ["Hel", "lo", "!"]


SSE_BODY_WITH_USAGE = (
    'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n'
    'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":3}}\n\n'
    "data: [DONE]\n\n"
)


def _completion_tokens_for_tenant_a(metrics_text: str) -> float:
    # The Prometheus registry is a process-wide singleton, so its counters
    # accumulate across every test in the session - comparing a before/
    # after delta is the only reliable assertion, not an absolute value.
    for line in metrics_text.splitlines():
        if line.startswith(
            'palisade_tenant_tokens_total{direction="completion",tenant="tenant-a"}'
        ):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


@respx.mock
def test_stream_usage_chunk_reconciles_the_budget_and_bills_the_tenant(
    client, auth_headers
):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(
            200,
            content=SSE_BODY_WITH_USAGE,
            headers={"content-type": "text/event-stream"},
        )
    )
    before = _completion_tokens_for_tenant_a(client.get("/metrics").text)

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
    ) as response:
        assert response.status_code == 200
        list(response.iter_lines())  # drain the stream so `finally` runs

    after = _completion_tokens_for_tenant_a(client.get("/metrics").text)
    assert after - before == 3


@respx.mock
def test_upstream_disconnecting_mid_stream_is_a_handled_upstream_error(
    client, auth_headers, caplog
):
    """Found live during M5's chaos day (docs/evidence/m5/02-*): killing
    vLLM mid-stream raised httpx.RemoteProtocolError, which propagated
    unhandled past relay()'s `except UpstreamError` - status_code stayed
    "200" and the audit log reported outcome="ok" for a request that
    actually failed. This is the regression test for the fix."""
    respx.post("http://upstream.test/v1/chat/completions").mock(
        side_effect=httpx.RemoteProtocolError(
            "peer closed connection without sending complete message body"
        )
    )

    with caplog.at_level(logging.INFO):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as response:
            assert response.status_code == 200  # headers already sent
            list(response.iter_lines())

    settled = [r for r in caplog.records if "chat_completion_settled" in r.getMessage()]
    assert settled, "no chat_completion_settled audit line was emitted"
    fields = settled[-1].extra_fields
    assert fields["outcome"] == "upstream_error"
    assert fields["status"] == 502
