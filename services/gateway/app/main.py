"""App factory with a lifespan-managed httpx client.

The client is created once, at startup, and reused for every request's
whole lifetime - see upstream.make_client for why. request_id middleware
runs first so every log line and error response carries an X-Request-ID,
including ones from exceptions raised before a route handler even runs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from starlette.responses import Response

from .cache import ResponseCache
from .config import settings
from .loadshed import InFlightLimiter
from .observability import configure_logging, new_request_id, request_id_var
from .routes import chat, health
from .tenancy import TenantStore, load_tenants
from .upstream import make_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.http_client = make_client()
    app.state.tenants = load_tenants()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.tenant_store = TenantStore(app.state.redis)
    app.state.response_cache = ResponseCache(app.state.redis)
    app.state.in_flight_limiter = InFlightLimiter(
        settings.max_in_flight_upstream_requests
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await app.state.redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Palisade Gateway", lifespan=lifespan)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or new_request_id()
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = req_id
        return response

    app.include_router(health.router)
    app.include_router(chat.router)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
