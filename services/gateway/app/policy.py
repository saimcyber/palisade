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

    return body
