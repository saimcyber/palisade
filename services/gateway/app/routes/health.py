"""Liveness vs readiness - deliberately different questions.

/healthz answers "is this process alive" and never talks to anything else -
a slow or dead upstream must not make Kubernetes restart a perfectly healthy
gateway container.

/readyz answers "are this gateway's dependencies reachable right now" by
checking vLLM and Redis, and must return 503, not 200, when either is down.
It is an operator's check, not the kubelet's readiness probe (ADR 0027):
every replica shares the same vLLM and Redis, so gating traffic on them
would pull all replicas at once and replace the gateway's own audited 503
with the ingress's anonymous one. The kubelet probes /healthz instead, and
the request path itself fails closed when a dependency is down.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..upstream import check_ready

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request, response: Response) -> dict[str, str]:
    client = request.app.state.http_client
    if not await check_ready(client):
        response.status_code = 503
        return {"status": "not ready", "reason": "upstream unreachable"}

    try:
        await request.app.state.redis.ping()
    except Exception:  # noqa: BLE001 - any Redis failure means "not ready"
        response.status_code = 503
        return {"status": "not ready", "reason": "redis unreachable"}

    return {"status": "ready"}
