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

from prometheus_client import Counter, Histogram

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
