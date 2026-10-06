"""The stated rule (observability.py's module docstring, ADR 0021/0022):
nothing ever logs prompt content. This is the test that actually proves
it, rather than trusting the comments."""

from __future__ import annotations

import logging

import respx
from httpx import Response

# A sentence, not a token-shaped string - a high-entropy value here trips
# gitleaks' generic-api-key heuristic even though it is a test fixture,
# not a credential.
SECRET_PROMPT = "please do not ever write this exact sentence to a log file"


@respx.mock
def test_prompt_content_never_appears_in_any_log_record(client, auth_headers, caplog):
    respx.post("http://upstream.test/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "1",
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            },
        )
    )
    with caplog.at_level(logging.DEBUG):
        response = client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json={
                "messages": [{"role": "user", "content": SECRET_PROMPT}],
                "max_tokens": 16,
            },
        )
    assert response.status_code == 200
    for record in caplog.records:
        assert SECRET_PROMPT not in record.getMessage()
        assert SECRET_PROMPT not in str(getattr(record, "extra_fields", ""))
