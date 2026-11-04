"""Labelled counters exist at 0 from startup, not from their first .inc().

Found by the M5 demo: after a gateway restart, tenant-b's first budget
rejection created palisade_budget_rejected_total{tenant="tenant-b"} with its
first-ever sample already at 1. increase() needs two samples to see a
change, so it reported 0 and PalisadeTenantBudgetExhausted never fired.
"""

from __future__ import annotations

import re

from prometheus_client import generate_latest

import app.main as main_module
from app.observability import initialise_labelled_counters


def _value(metrics_text: str, series: str) -> float | None:
    m = re.search(rf"^{re.escape(series)} ([0-9.e+-]+)$", metrics_text, re.M)
    return float(m.group(1)) if m else None


def test_initialise_creates_every_alerted_series_at_zero():
    initialise_labelled_counters(["tenant-never-seen"])
    text = generate_latest().decode()

    assert (
        _value(text, 'palisade_budget_rejected_total{tenant="tenant-never-seen"}')
        == 0.0
    )
    assert (
        _value(text, 'palisade_rate_limited_total{tenant="tenant-never-seen"}') == 0.0
    )
    # The exposition format here lists labels sorted by name.
    assert (
        _value(
            text,
            'palisade_tenant_tokens_total{direction="completion",tenant="tenant-never-seen"}',
        )
        == 0.0
    )
    # The series these alert rules key on must exist before the first event.
    assert (
        _value(text, 'palisade_prompt_guard_blocks_total{reason="injection_suspected"}')
        is not None
    )
    assert (
        _value(
            text,
            'palisade_http_requests_total{method="POST",route="/v1/chat/completions",status="502"}',
        )
        is not None
    )


def test_initialise_does_not_create_budget_gauges():
    """A gauge at 0 would claim the tenant has no budget left."""
    initialise_labelled_counters(["tenant-gauge-check"])
    text = generate_latest().decode()
    assert 'palisade_tenant_budget_remaining{tenant="tenant-gauge-check"}' not in text


def test_startup_initialises_series_for_every_configured_tenant(
    monkeypatch, fake_redis
):
    seen: list[list[str]] = []
    monkeypatch.setattr(
        main_module,
        "initialise_labelled_counters",
        lambda names: seen.append(sorted(names)),
    )
    from fastapi.testclient import TestClient

    with TestClient(main_module.create_app()):
        pass

    assert seen == [["tenant-a", "tenant-b"]]
