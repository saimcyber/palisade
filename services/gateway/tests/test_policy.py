"""policy.py: thinking disabled by default and overridable, max_tokens
clamped, model name pinned - see docs/adr/0006-server-side-request-policy.md.
"""

from __future__ import annotations

from app.policy import apply_policy, estimate_tokens


def test_thinking_disabled_by_default():
    body = apply_policy({"messages": []})
    assert body["chat_template_kwargs"]["enable_thinking"] is False


def test_thinking_can_be_explicitly_overridden():
    body = apply_policy(
        {"messages": [], "chat_template_kwargs": {"enable_thinking": True}}
    )
    assert body["chat_template_kwargs"]["enable_thinking"] is True


def test_max_tokens_defaults_to_ceiling_when_absent():
    body = apply_policy({"messages": []})
    assert body["max_tokens"] == 512


def test_max_tokens_above_ceiling_is_clamped():
    body = apply_policy({"messages": [], "max_tokens": 10_000})
    assert body["max_tokens"] == 512


def test_max_tokens_below_ceiling_is_left_alone():
    body = apply_policy({"messages": [], "max_tokens": 16})
    assert body["max_tokens"] == 16


def test_model_name_is_always_pinned():
    body = apply_policy({"messages": [], "model": "whatever-the-caller-wants"})
    assert body["model"] == "palisade-small"


def test_streaming_requests_get_usage_forced_on():
    body = apply_policy({"messages": [], "stream": True})
    assert body["stream_options"]["include_usage"] is True


def test_streaming_requests_keep_other_stream_options():
    body = apply_policy(
        {"messages": [], "stream": True, "stream_options": {"custom": True}}
    )
    assert body["stream_options"] == {"custom": True, "include_usage": True}


def test_non_streaming_requests_get_no_stream_options():
    body = apply_policy({"messages": []})
    assert "stream_options" not in body


def test_estimate_tokens_grows_with_prompt_length():
    small = estimate_tokens({"messages": [{"content": "hi"}], "max_tokens": 10})
    large = estimate_tokens({"messages": [{"content": "x" * 1000}], "max_tokens": 10})
    assert large > small


def test_estimate_tokens_includes_the_completion_ceiling():
    estimate = estimate_tokens({"messages": [{"content": ""}], "max_tokens": 100})
    assert estimate >= 100
