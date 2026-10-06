"""The gateway's actual purpose: /v1/models and /v1/chat/completions.

Kept OpenAI-compatible on purpose (docs/adr/0004-openai-compatible-api.md) -
an existing client library or eval harness should be able to point at this
gateway by changing only a base URL and an API key.

Every request that reaches the upstream has already passed, in order: rate
limit -> input guard -> budget reservation -> cache lookup. Each is cheaper
than the one after it (docs/adr/0021), so the expensive resource - the GPU -
is protected by a series of progressively more expensive filters.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import authenticate
from ..guard import PromptRejected, apply_guard
from ..observability import (
    budget_rejected_total,
    cache_tokens_saved_total,
    http_request_duration_seconds,
    http_requests_total,
    log_event,
    rate_limited_total,
    request_id_var,
    tenant_budget_remaining,
    tenant_tokens_total,
    tokens_total,
)
from ..policy import apply_policy, estimate_tokens
from ..tenancy import Tenant
from ..upstream import (
    UpstreamError,
    chat_completion,
    list_models,
    stream_chat_completion,
)

router = APIRouter()
logger = logging.getLogger("palisade.chat")


def _usage_total(usage: dict) -> int:
    return int(usage.get("prompt_tokens", 0)) + int(usage.get("completion_tokens", 0))


def _record_usage(tenant: Tenant, usage: dict, *, generated: bool) -> None:
    """Records a response's usage against the tenant (always) and, only
    when `generated` is true, against the platform-wide GPU-work counter
    too - a cache hit bills the tenant (ADR 0021) but did no GPU work, so
    it must not inflate the GPU dashboard's tokens/sec panel."""
    tenant_tokens_total.labels(tenant=tenant.name, direction="prompt").inc(
        usage.get("prompt_tokens", 0)
    )
    tenant_tokens_total.labels(tenant=tenant.name, direction="completion").inc(
        usage.get("completion_tokens", 0)
    )
    if generated:
        tokens_total.labels(direction="prompt").inc(usage.get("prompt_tokens", 0))
        tokens_total.labels(direction="completion").inc(
            usage.get("completion_tokens", 0)
        )
    else:
        cache_tokens_saved_total.inc(_usage_total(usage))


async def _refresh_budget_gauge(tenant_store, tenant: Tenant) -> None:
    used = await tenant_store.budget_used(tenant)
    tenant_budget_remaining.labels(tenant=tenant.name).set(
        max(tenant.token_budget - used, 0)
    )


def _audit(
    tenant: Tenant,
    *,
    outcome: str,
    status: int,
    start: float,
    usage: dict | None = None,
    cache_hit: bool = False,
) -> None:
    """The one structured audit line per request the plan calls for -
    tenant and outcome, never prompt content. Emitted at every terminal
    point (rejections included), not just on a successful request."""
    usage = usage or {}
    log_event(
        logger,
        "chat_completion_settled",
        tenant=tenant.name,
        outcome=outcome,
        status=status,
        cache_hit=cache_hit,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        duration_ms=round((time.monotonic() - start) * 1000, 1),
    )


@router.get("/v1/models")
async def get_models(request: Request, tenant: Tenant = Depends(authenticate)) -> dict:
    client = request.app.state.http_client
    start = time.monotonic()
    try:
        data = await list_models(client, request_id_var.get())
        http_requests_total.labels(route="/v1/models", method="GET", status="200").inc()
        return data
    except UpstreamError as exc:
        http_requests_total.labels(
            route="/v1/models", method="GET", status=str(exc.status_code)
        ).inc()
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    finally:
        http_request_duration_seconds.labels(route="/v1/models", method="GET").observe(
            time.monotonic() - start
        )


@router.post("/v1/chat/completions", response_model=None)
async def create_chat_completion(
    request: Request, tenant: Tenant = Depends(authenticate)
) -> StreamingResponse | JSONResponse:
    client = request.app.state.http_client
    tenant_store = request.app.state.tenant_store
    response_cache = request.app.state.response_cache
    request_id = request_id_var.get()
    start = time.monotonic()

    if not await tenant_store.check_rate_limit(tenant):
        rate_limited_total.labels(tenant=tenant.name).inc()
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status="429"
        ).inc()
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
        _audit(tenant, outcome="rate_limited", status=429, start=start)
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited"},
            headers={"Retry-After": "1"},
        )

    body = await request.json()

    try:
        body = apply_guard(body)
    except PromptRejected as exc:
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status="400"
        ).inc()
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
        _audit(tenant, outcome=exc.reason, status=400, start=start)
        return JSONResponse(status_code=400, content={"error": exc.reason})

    body = apply_policy(body)
    reservation = estimate_tokens(body)

    if not await tenant_store.reserve_budget(tenant, reservation):
        budget_rejected_total.labels(tenant=tenant.name).inc()
        await _refresh_budget_gauge(tenant_store, tenant)
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status="429"
        ).inc()
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
        _audit(tenant, outcome="budget_exhausted", status=429, start=start)
        return JSONResponse(status_code=429, content={"error": "budget_exhausted"})

    await _refresh_budget_gauge(tenant_store, tenant)

    log_event(
        logger,
        "chat_completion_request",
        tenant=tenant.name,
        stream=bool(body.get("stream")),
        max_tokens=body.get("max_tokens"),
    )

    if body.get("stream"):

        async def relay():
            status_code = "200"
            usage: dict | None = None
            try:
                async for chunk, maybe_usage in stream_chat_completion(
                    client, body, start, request_id
                ):
                    if maybe_usage:
                        usage = maybe_usage
                    yield chunk
            except UpstreamError as exc:
                status_code = str(exc.status_code)
                yield f'data: {{"error": "{exc.detail}"}}\n\n'.encode()
            finally:
                if usage:
                    await tenant_store.adjust_budget(
                        tenant, _usage_total(usage) - reservation
                    )
                    _record_usage(tenant, usage, generated=True)
                    await _refresh_budget_gauge(tenant_store, tenant)
                else:
                    # Nothing usable came back (error, or a disconnect
                    # before the final chunk) - keep the full reservation
                    # rather than refund it, since the upstream may have
                    # already generated tokens we have no count for.
                    pass
                http_requests_total.labels(
                    route="/v1/chat/completions", method="POST", status=status_code
                ).inc()
                http_request_duration_seconds.labels(
                    route="/v1/chat/completions", method="POST"
                ).observe(time.monotonic() - start)
                _audit(
                    tenant,
                    outcome="ok" if status_code == "200" else "upstream_error",
                    status=int(status_code),
                    start=start,
                    usage=usage,
                )

        return StreamingResponse(relay(), media_type="text/event-stream")

    cached = await response_cache.get(tenant.key_hash, body)
    if cached is not None:
        usage = cached.get("usage") or {}
        await tenant_store.adjust_budget(tenant, _usage_total(usage) - reservation)
        _record_usage(tenant, usage, generated=False)
        await _refresh_budget_gauge(tenant_store, tenant)
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status="200"
        ).inc()
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
        _audit(
            tenant, outcome="ok", status=200, start=start, usage=usage, cache_hit=True
        )
        return JSONResponse(content=cached)

    try:
        data = await chat_completion(client, body, request_id)
    except UpstreamError as exc:
        await tenant_store.adjust_budget(tenant, -reservation)
        await _refresh_budget_gauge(tenant_store, tenant)
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status=str(exc.status_code)
        ).inc()
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
        _audit(tenant, outcome="upstream_error", status=exc.status_code, start=start)
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    usage = data.get("usage") or {}
    await tenant_store.adjust_budget(tenant, _usage_total(usage) - reservation)
    _record_usage(tenant, usage, generated=True)
    await _refresh_budget_gauge(tenant_store, tenant)
    await response_cache.set(tenant.key_hash, body, data)
    http_requests_total.labels(
        route="/v1/chat/completions", method="POST", status="200"
    ).inc()
    http_request_duration_seconds.labels(
        route="/v1/chat/completions", method="POST"
    ).observe(time.monotonic() - start)
    _audit(tenant, outcome="ok", status=200, start=start, usage=usage)
    return JSONResponse(content=data)
