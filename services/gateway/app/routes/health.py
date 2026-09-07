"""Liveness vs readiness - deliberately different questions.

/healthz answers "is this process alive" and never talks to anything else -
a slow or dead upstream must not make Kubernetes restart a perfectly healthy
gateway container.

/readyz answers "can this gateway actually serve a request right now" by
checking the upstream. This is what Kubernetes gates traffic on, and it is
also the case that is usually left untested: it must return 503, not 200,
when the upstream is down.
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
    if await check_ready(client):
        return {"status": "ready"}
    response.status_code = 503
    return {"status": "not ready", "reason": "upstream unreachable"}
