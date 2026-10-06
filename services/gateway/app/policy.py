"""Server-side request policy - the actual argument for having a gateway.

Three things a raw client of vLLM could do that this platform does not let
it do:

1. leave Qwen3 in its default "thinking" mode and pay for/see <think> blocks
   nobody asked for (confirmed live in the M1 Task 2 spike: it does this by
   default);
2. ask for unbounded generation;
3. address a model that was never intended to be served.

See docs/adr/0006-server-side-request-policy.md for why these are decided by
the platform rather than left to the caller.
"""

from __future__ import annotations

from typing import Any

from .config import settings


def apply_policy(body: dict[str, Any]) -> dict[str, Any]:
    """Mutates and returns a copy of the incoming request body."""
    body = dict(body)

    # Pin the model name regardless of what the caller sent - there is
    # exactly one model behind this gateway (docs/adr/0005).
    body["model"] = settings.served_model_name

    # Clamp max_tokens: a caller may ask for less than the ceiling, never
    # more. Absence gets the ceiling, not "unbounded".
    requested = body.get("max_tokens")
    if requested is None or requested > settings.max_tokens_ceiling:
        body["max_tokens"] = settings.max_tokens_ceiling

    # Qwen3's chat template accepts enable_thinking via chat_template_kwargs.
    # Default it off; a caller can still explicitly ask for it.
    kwargs = dict(body.get("chat_template_kwargs") or {})
    kwargs.setdefault("enable_thinking", settings.default_enable_thinking)
    body["chat_template_kwargs"] = kwargs

    # Token-budget reconciliation (tenancy.py) needs real usage numbers even
    # on the streaming path. vLLM only emits a final usage-bearing chunk if
    # asked - forced on here, regardless of what the caller sent.
    if body.get("stream"):
        stream_options = dict(body.get("stream_options") or {})
        stream_options["include_usage"] = True
        body["stream_options"] = stream_options

    return body


def estimate_tokens(body: dict[str, Any]) -> int:
    """Pre-flight token estimate, before any real usage exists.

    Deliberately crude (chars / estimate_chars_per_token, plus a fixed
    per-message overhead for the chat template's own wrapper tokens and
    the role markers) - this only gates whether a reservation is allowed,
    and the reconciliation step in chat.py corrects it to the real number
    as soon as one exists.

    This is a rough estimate, not a guaranteed overestimate: a prompt
    whose real tokenisation is denser than estimate_chars_per_token
    assumes (e.g. a lot of non-English text or code) can still reserve
    less than it actually uses, and the uncapped INCRBY in
    tenancy.reserve_budget means a tenant can end a window slightly over
    its nominal budget rather than being blocked exactly at it. Stated
    here as a known limitation, not fixed for this milestone - closing it
    exactly would need the same tokenizer vLLM uses, which is a real
    dependency for a number that only has to be approximately right.
    """
    message_overhead_tokens = 4  # role marker + template wrapper, per message
    messages = [m for m in body.get("messages", []) if isinstance(m, dict)]
    text_chars = sum(len(str(m.get("content", ""))) for m in messages)
    prompt_estimate = (
        int(text_chars / settings.estimate_chars_per_token)
        + len(messages) * message_overhead_tokens
        + 1
    )
    completion_ceiling = body.get("max_tokens") or settings.max_tokens_ceiling
    return prompt_estimate + completion_ceiling
