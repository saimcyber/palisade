"""One integration test against a real vLLM - skipped by default since it
needs a GPU and a running model server. Run explicitly with:

    PALISADE_RUN_GPU_TESTS=1 pytest tests/test_integration.py

against `docker compose --profile full up` or `make vllm-up` (port-forwarded
to localhost:8000).
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PALISADE_RUN_GPU_TESTS") != "1",
    reason="needs a GPU and a running vLLM - set PALISADE_RUN_GPU_TESTS=1 to run",
)


def test_real_streaming_completion_against_vllm(auth_headers):
    # Talks to the gateway directly assuming it's already running with a
    # real upstream configured (compose or a port-forwarded k8s Service) -
    # this test does not build the app in-process like the mocked tests do,
    # since the point is to exercise the real network path end to end.
    base_url = os.environ.get("PALISADE_GATEWAY_URL", "http://localhost:8080")
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=auth_headers,
            json={
                "messages": [
                    {"role": "user", "content": "Say hello in exactly three words."}
                ],
                "stream": True,
                "max_tokens": 30,
            },
        ) as response:
            assert response.status_code == 200
            chunk_count = sum(
                1 for line in response.iter_lines() if line.startswith("data:")
            )
            assert chunk_count > 1, (
                "expected more than one SSE chunk - streaming may be buffered"
            )
