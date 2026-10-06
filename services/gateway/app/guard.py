"""Input guard: injection heuristics, PII redaction, length clamps.

Deliberately simple, keyword/regex-based detection - documented as defence
in depth, not a solved problem (see docs/adr/0022-prompt-guard-heuristics.md
for what this does and does not catch, and why a heavier model-based guard
was ruled out for this milestone). Every decision this module makes is a
labelled metric; none of it logs prompt content.
"""

from __future__ import annotations

import re
from typing import Any

from .config import settings
from .observability import prompt_guard_blocks_total

# Intentionally coarse - catches the textbook "ignore your instructions"
# family of attacks without pretending to be a complete jailbreak filter.
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore (all |your )?(previous|prior|above) instructions",
        r"disregard (all |your )?(previous|prior|above) (instructions|prompt)",
        r"you are now (in )?(developer|dan|jailbreak) mode",
        r"reveal your (system prompt|instructions)",
    ]
]

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


class PromptRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _message_text(body: dict[str, Any]) -> str:
    return " ".join(
        str(m.get("content", ""))
        for m in body.get("messages", [])
        if isinstance(m, dict)
    )


def apply_guard(body: dict[str, Any]) -> dict[str, Any]:
    """Raises PromptRejected for injection/length violations; otherwise
    returns a copy of `body` with PII redacted in place."""
    text = _message_text(body)

    if len(text) > settings.max_prompt_chars:
        prompt_guard_blocks_total.labels(reason="length_exceeded").inc()
        raise PromptRejected("length_exceeded")

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            prompt_guard_blocks_total.labels(reason="injection_suspected").inc()
            raise PromptRejected("injection_suspected")

    body = dict(body)
    messages = []
    redacted_any = False
    for message in body.get("messages", []):
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            messages.append(message)
            continue
        content = message["content"]
        for kind, pattern in _PII_PATTERNS:
            new_content, n = pattern.subn(f"[REDACTED_{kind.upper()}]", content)
            if n:
                redacted_any = True
                content = new_content
        messages.append({**message, "content": content})
    body["messages"] = messages

    if redacted_any:
        prompt_guard_blocks_total.labels(reason="pii_redacted").inc()

    return body
