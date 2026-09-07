"""Streaming: chunks are relayed in order, unmodified, and without buffering
the whole response first - buffering would silently turn TTFT into "time to
last token" without any single assertion catching it, so order is what a
unit test can verify; the acceptance test (M1 Verification table) is what
actually proves live incremental delivery against a real vLLM.
"""

from __future__ import annotations

import json

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
