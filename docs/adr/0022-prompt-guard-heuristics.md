# 22. Prompt guard: regex heuristics, not a model

- **Status:** Accepted

## Context

The plan calls for an input guard - injection heuristics, PII redaction,
length clamps - with every block a labelled metric. The real options for
"injection heuristics" are a keyword/regex filter, or a second model call
(a classifier or the serving model itself) that judges each prompt before
it reaches vLLM.

A second model call was ruled out for this milestone: this platform has
exactly one GPU and one model replica (docs/adr/0005), already budgeted for
serving traffic. Spending a generation on every request just to decide
whether to allow it would roughly double GPU time per request on hardware
that is already the project's tightest constraint, for a guard whose
accuracy nobody has evaluated yet.

## Decision

`guard.py` is a small, explicit set of checks, run in this order because
each is cheaper than the next:

1. **Length clamp** - reject prompts over `max_prompt_chars`.
2. **Injection heuristics** - reject on a short list of regexes for the
   textbook "ignore your instructions" / "developer mode" family of
   attacks.
3. **PII redaction** - email, SSN and credit-card-shaped patterns are
   replaced with a `[REDACTED_*]` placeholder in the forwarded body, not
   blocked - redaction lets a legitimate request through without the
   model ever seeing the raw value.

Every decision increments `palisade_prompt_guard_blocks_total{reason=...}`
and nothing here logs prompt content, consistent with observability.py's
rule for the rest of the gateway.

## Consequences

- This catches the textbook cases and nothing subtler - a determined
  attacker using synonyms, encoding, or multi-turn framing will not be
  caught. That is a stated limitation, not a gap discovered later: this is
  defence in depth, one layer among several (rate limits, budgets, no
  outbound network from vLLM), not a claim that prompt injection is solved.
- The PII patterns are deliberately narrow (three shapes) to keep the false
  positive rate low; broadening them is cheap to do later and does not
  change any caller-visible contract, since redaction already degrades
  gracefully.
- A model-based guard remains an explicit option for a later milestone if
  the keyword approach proves too coarse in practice - nothing in `guard.py`
  or `chat.py` assumes the check is synchronous-and-free; replacing
  `apply_guard` with an async call is a local change.
