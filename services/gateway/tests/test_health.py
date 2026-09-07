"""/healthz never touches the upstream; /readyz does, and must fail when the
upstream is down - the case that matters and the one usually left untested.
"""

from __future__ import annotations

import httpx
import respx
from httpx import Response


def test_healthz_never_calls_upstream(client):
    with respx.mock(assert_all_called=False) as router:
        route = router.get("http://upstream.test/health")
        response = client.get("/healthz")
        assert response.status_code == 200
        assert route.call_count == 0


@respx.mock
def test_readyz_is_ready_when_upstream_healthy(client):
    respx.get("http://upstream.test/health").mock(return_value=Response(200))
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@respx.mock
def test_readyz_returns_503_when_upstream_down(client):
    respx.get("http://upstream.test/health").mock(
        side_effect=httpx.ConnectError("refused")
    )
    response = client.get("/readyz")
    assert response.status_code == 503


@respx.mock
def test_readyz_returns_503_when_upstream_unhealthy(client):
    respx.get("http://upstream.test/health").mock(return_value=Response(500))
    response = client.get("/readyz")
    assert response.status_code == 503
