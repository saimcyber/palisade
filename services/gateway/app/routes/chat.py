"""The gateway's actual purpose: /v1/models and /v1/chat/completions.

Kept OpenAI-compatible on purpose (docs/adr/0004-openai-compatible-api.md) -
an existing client library or eval harness should be able to point at this
gateway by changing only a base URL and an API key.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import authenticate
from ..observability import (
    http_request_duration_seconds,
    http_requests_total,
    log_event,
)
from ..policy import apply_policy
from ..upstream import (
    UpstreamError,
    chat_completion,
    list_models,
    stream_chat_completion,
)

router = APIRouter()
logger = logging.getLogger("palisade.chat")


@router.get("/v1/models")
async def get_models(request: Request, tenant: str = Depends(authenticate)) -> dict:
    client = request.app.state.http_client
    start = time.monotonic()
    try:
        data = await list_models(client)
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
    request: Request, tenant: str = Depends(authenticate)
) -> StreamingResponse | JSONResponse:
    client = request.app.state.http_client
    start = time.monotonic()
    body = await request.json()
    body = apply_policy(body)

    log_event(
        logger,
        "chat_completion_request",
        tenant=tenant,
        stream=bool(body.get("stream")),
        max_tokens=body.get("max_tokens"),
    )

    if body.get("stream"):

        async def relay():
            try:
                async for chunk in stream_chat_completion(client, body, start):
                    yield chunk
            except UpstreamError as exc:
                http_requests_total.labels(
                    route="/v1/chat/completions",
                    method="POST",
                    status=str(exc.status_code),
                ).inc()
                yield f'data: {{"error": "{exc.detail}"}}\n\n'.encode()
            finally:
                http_requests_total.labels(
                    route="/v1/chat/completions", method="POST", status="200"
                ).inc()
                http_request_duration_seconds.labels(
                    route="/v1/chat/completions", method="POST"
                ).observe(time.monotonic() - start)

        return StreamingResponse(relay(), media_type="text/event-stream")

    try:
        data = await chat_completion(client, body)
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status="200"
        ).inc()
        return JSONResponse(content=data)
    except UpstreamError as exc:
        http_requests_total.labels(
            route="/v1/chat/completions", method="POST", status=str(exc.status_code)
        ).inc()
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    finally:
        http_request_duration_seconds.labels(
            route="/v1/chat/completions", method="POST"
        ).observe(time.monotonic() - start)
