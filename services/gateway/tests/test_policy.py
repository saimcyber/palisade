"""policy.py: thinking disabled by default and overridable, max_tokens
clamped, model name pinned - see docs/adr/0006-server-side-request-policy.md.
"""

from __future__ import annotations

from app.policy import apply_policy


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
