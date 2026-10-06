"""API key authentication.

Only the SHA-256 hash of each accepted key is ever held in memory or
compared against - a dump of this process's config or memory yields no
usable credential, only hashes. Keys are of the form `plsd_<random>`; the
prefix is cosmetic (helps a human or a secret scanner spot one) and carries
no meaning to the gateway itself.

The accepted hash -> Tenant map is built once at startup (app.state.tenants,
from tenancy.load_tenants()) and looked up here; it is never mutated at
request time. The things that change per request - rate limit counters,
budget usage - live in Redis and are checked later, in chat.py, once we
know which Tenant this is.
"""

from __future__ import annotations

import hashlib

from fastapi import Header, HTTPException, Request, status

from .observability import auth_failures_total
from .tenancy import Tenant


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def authenticate(
    request: Request, authorization: str | None = Header(default=None)
) -> Tenant:
    """FastAPI dependency: returns the caller's Tenant or 401s."""
    if authorization is None or not authorization.startswith("Bearer "):
        auth_failures_total.labels(reason="missing_header").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key:
        auth_failures_total.labels(reason="malformed_header").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    key_hash = _hash(raw_key)
    tenant = request.app.state.tenants.get(key_hash)
    if tenant is None:
        auth_failures_total.labels(reason="unknown_key").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return tenant
