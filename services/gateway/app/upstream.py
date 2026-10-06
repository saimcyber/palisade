"""Talks to the model server (vLLM) and relays its responses.

The streaming path relays SSE chunks straight through as they arrive -
buffering would silently destroy the streaming behaviour the acceptance test
checks for, and would turn TTFT into "time to last token" without anyone
noticing until a user complained.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import settings
from .observability import time_to_first_token_seconds, upstream_errors_total

logger = logging.getLogger("palisade.upstream")


class UpstreamError(Exception):
    """Raised when the upstream model server cannot serve a request."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def make_client() -> httpx.AsyncClient:
    """Built once in the app's lifespan and reused for every request -
    creating a new connection pool per request would defeat keep-alive and
    add needless latency to every call."""
    return httpx.AsyncClient(
        base_url=settings.upstream_base_url,
        timeout=settings.upstream_timeout_seconds,
    )


async def check_ready(client: httpx.AsyncClient) -> bool:
    """Used by /readyz - this is what Kubernetes gates traffic on."""
    try:
        response = await client.get("/health", timeout=5.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def list_models(client: httpx.AsyncClient, request_id: str) -> dict[str, Any]:
    try:
        response = await client.get("/v1/models", headers={"X-Request-ID": request_id})
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as exc:
        upstream_errors_total.labels(kind="connect").inc()
        raise UpstreamError(503, "Upstream model server unreachable") from exc
    except httpx.TimeoutException as exc:
        upstream_errors_total.labels(kind="timeout").inc()
        raise UpstreamError(504, "Upstream model server timed out") from exc
    except httpx.HTTPStatusError as exc:
        upstream_errors_total.labels(kind="http_status").inc()
        raise UpstreamError(exc.response.status_code, exc.response.text) from exc


async def chat_completion(
    client: httpx.AsyncClient, body: dict[str, Any], request_id: str
) -> dict[str, Any]:
    """Non-streaming path."""
    try:
        response = await client.post(
            "/v1/chat/completions", json=body, headers={"X-Request-ID": request_id}
        )
        response.raise_for_status()
    except httpx.ConnectError as exc:
        upstream_errors_total.labels(kind="connect").inc()
        raise UpstreamError(503, "Upstream model server unreachable") from exc
    except httpx.TimeoutException as exc:
        upstream_errors_total.labels(kind="timeout").inc()
        raise UpstreamError(504, "Upstream model server timed out") from exc
    except httpx.HTTPStatusError as exc:
        upstream_errors_total.labels(kind="http_status").inc()
        raise UpstreamError(exc.response.status_code, exc.response.text) from exc

    # tokens_total/tenant_tokens_total are recorded by chat.py's
    # _record_usage, not here - that's the one place that knows whether
    # this usage came from a real generation or a cache hit (ADR 0021),
    # which is exactly the distinction that metric needs to preserve.
    return response.json()


async def stream_chat_completion(
    client: httpx.AsyncClient,
    body: dict[str, Any],
    request_start: float,
    request_id: str,
) -> AsyncIterator[tuple[bytes, dict[str, Any] | None]]:
    """Streaming path: relays raw SSE lines through unmodified and unbuffered.

    TTFT is measured here, at the first non-empty chunk received from the
    upstream - not at connection open, which would understate it, and not
    at first byte written to the client, which this process does not
    control precisely enough to matter.

    Each item is (line_bytes, usage). `usage` is None for every chunk
    except the final one - policy.apply_policy forces
    `stream_options.include_usage`, so vLLM's last data chunk before
    `[DONE]` carries real prompt/completion token counts, which chat.py
    uses to reconcile the pre-flight budget reservation against the
    tenant's actual usage.
    """
    first_token_seen = False

    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json=body,
            headers={"X-Request-ID": request_id},
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                upstream_errors_total.labels(kind="http_status").inc()
                raise UpstreamError(
                    response.status_code, error_body.decode(errors="replace")
                )

            async for line in response.aiter_lines():
                if not line:
                    continue
                usage = None
                if line.startswith("data:") and line.strip() != "data: [DONE]":
                    if not first_token_seen:
                        time_to_first_token_seconds.observe(
                            time.monotonic() - request_start
                        )
                        first_token_seen = True
                    payload = line.removeprefix("data:").strip()
                    try:
                        chunk = json.loads(payload)
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                    except json.JSONDecodeError:
                        pass
                yield (line + "\n\n").encode("utf-8"), usage
    except httpx.ConnectError as exc:
        upstream_errors_total.labels(kind="connect").inc()
        raise UpstreamError(503, "Upstream model server unreachable") from exc
    except httpx.TimeoutException as exc:
        upstream_errors_total.labels(kind="timeout").inc()
        raise UpstreamError(504, "Upstream model server timed out") from exc
