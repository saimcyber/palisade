"""API key authentication.

Only the SHA-256 hash of each accepted key is ever held in memory or
compared against - a dump of this process's config or memory yields no
usable credential, only hashes. Keys are of the form `plsd_<random>`; the
prefix is cosmetic (helps a human or a secret scanner spot one) and carries
no meaning to the gateway itself.

M1: hashes come from a single env var, loaded once at startup - fine for one
operator. M4 moves the lookup to Redis so keys can be issued/revoked without
a redeploy; nothing above this module (routes, tests) needs to change for
that, only the body of `authenticate`.
"""

from __future__ import annotations

import hashlib

from fastapi import Header, HTTPException, status

from .config import settings
from .observability import auth_failures_total


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _accepted_hashes() -> set[str]:
    return {h.strip() for h in settings.api_key_hashes.split(",") if h.strip()}


async def authenticate(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: returns the key's hash (used as a tenant id) or 401s.

    The hash - not the raw key - is what callers get back as their identity,
    since the raw key is never retained past this function.
    """
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
    if key_hash not in _accepted_hashes():
        auth_failures_total.labels(reason="unknown_key").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return key_hash
