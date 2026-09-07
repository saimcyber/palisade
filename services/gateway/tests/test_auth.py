"""Auth: valid key, unknown key, missing header, malformed header."""

from __future__ import annotations

import respx
from httpx import Response


@respx.mock
def test_valid_key_is_accepted(client, auth_headers):
    respx.get("http://upstream.test/v1/models").mock(
        return_value=Response(200, json={"object": "list", "data": []})
    )
    response = client.get("/v1/models", headers=auth_headers)
    assert response.status_code == 200


def test_unknown_key_is_rejected(client):
    response = client.get(
        "/v1/models", headers={"Authorization": "Bearer not-a-real-key"}
    )
    assert response.status_code == 401


def test_missing_header_is_rejected(client):
    response = client.get("/v1/models")
    assert response.status_code == 401


def test_malformed_header_is_rejected(client):
    response = client.get("/v1/models", headers={"Authorization": "not-bearer-shaped"})
    assert response.status_code == 401


def test_empty_bearer_token_is_rejected(client):
    response = client.get("/v1/models", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
