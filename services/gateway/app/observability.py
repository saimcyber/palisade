"""Metrics, structured logging, and request IDs.

Everything here is deliberately silent about prompt content - counts and
latencies only. A log line or metric label that leaked prompt text would be
a privacy incident wearing an observability costume.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from prometheus_client import Counter, Gauge, Histogram

from .config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# --- metrics -----------------------------------------------------------------

http_requests_total = Counter(
    "palisade_http_requests_total",
    "HTTP requests handled",
    ["route", "method", "status"],
)

http_request_duration_seconds = Histogram(
    "palisade_http_request_duration_seconds",
    "Total request duration, from receipt to final byte",
    ["route", "method"],
)

# Time to first token, tracked separately from total duration: in a chat UI
# TTFT is what a user actually feels, and it can be a small fraction of a
# long generation's total duration.
time_to_first_token_seconds = Histogram(
    "palisade_time_to_first_token_seconds",
    "Time from request receipt to the first streamed token",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

tokens_total = Counter(
    "palisade_tokens_total",
    "Tokens observed, by direction",
    ["direction"],  # prompt | completion
)

# Tenant-labelled: the cardinality is bounded by the number of tenants
# (small, operator-provisioned), which is what makes a per-tenant label
# safe here where it would not be on, say, a path or user-agent.
tenant_tokens_total = Counter(
    "palisade_tenant_tokens_total",
    "Tokens billed to a tenant's budget, by direction",
    ["tenant", "direction"],  # prompt | completion
)

tenant_budget_remaining = Gauge(
    "palisade_tenant_budget_remaining",
    "Tokens left in the tenant's current budget window",
    ["tenant"],
)

rate_limited_total = Counter(
    "palisade_rate_limited_total",
    "Requests rejected for exceeding the per-tenant rate limit",
    ["tenant"],
)

budget_rejected_total = Counter(
    "palisade_budget_rejected_total",
    "Requests rejected for exceeding the tenant's token budget",
    ["tenant"],
)

cache_hits_total = Counter("palisade_cache_hits_total", "Response cache hits")

cache_misses_total = Counter("palisade_cache_misses_total", "Response cache misses")

cache_tokens_saved_total = Counter(
    "palisade_cache_tokens_saved_total",
    "Tokens a cache hit served without a GPU generation - the cached response's own usage",
)

prompt_guard_blocks_total = Counter(
    "palisade_prompt_guard_blocks_total",
    "Requests the input guard blocked or modified, by reason",
    ["reason"],  # length_exceeded | injection_suspected | pii_redacted
)

load_shed_total = Counter(
    "palisade_load_shed_total",
    "Requests rejected with 503 because too many were already in flight to vLLM",
)

redis_errors_total = Counter(
    "palisade_redis_errors_total",
    "Requests that failed because Redis was unreachable or timed out mid-request",
)

upstream_in_flight = Gauge(
    "palisade_upstream_in_flight",
    "Requests currently waiting on a response from vLLM",
)

upstream_errors_total = Counter(
    "palisade_upstream_errors_total",
    "Errors talking to the upstream model server",
    ["kind"],  # timeout | connect | http_status
)

auth_failures_total = Counter(
    "palisade_auth_failures_total",
    "Rejected authentication attempts",
    ["reason"],  # missing_header | malformed_header | unknown_key
)


# --- structured JSON logging --------------------------------------------------


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)


def log_event(logger: logging.Logger, message: str, **fields: object) -> None:
    logger.info(message, extra={"extra_fields": fields})


def new_request_id() -> str:
    return uuid.uuid4().hex


class Timer:
    """Small helper so route code reads as `with Timer() as t: ...` then `t.elapsed`."""

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.elapsed = time.monotonic() - self._start
