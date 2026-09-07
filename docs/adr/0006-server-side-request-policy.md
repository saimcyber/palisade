# 6. Server-side request policy

- **Status:** Accepted

## Context

A raw client of vLLM can set `enable_thinking`, `max_tokens`, and `model` to
whatever it wants, or leave them out and get vLLM's defaults. Three concrete
problems surfaced from actually running the model (M1 Task 2 spike):

1. Qwen3 emits a `<think>...</think>` block by default. Confirmed live: an
   unmodified request to `palisade-small` produced one unprompted. A caller
   who doesn't know to ask for `enable_thinking: false` pays for and
   receives tokens nobody wanted.
2. Nothing stops a caller from requesting an unbounded (or very large)
   `max_tokens`, which on a single-GPU, single-replica tier (docs/adr/0005)
   is a direct path to starving every other request.
3. Nothing stops a caller from naming a different `model` in the request
   body - meaningless here since exactly one model is served, but a caller
   should get a clear, deliberate answer rather than whatever vLLM happens
   to do with an unrecognised name.

## Decision

`policy.py` rewrites every request before it reaches vLLM:

- `chat_template_kwargs.enable_thinking` defaults to `false`, set only if
  the caller did not already specify it - so a caller who explicitly wants
  reasoning traces can still ask for them.
- `max_tokens` is clamped to a configured ceiling; a caller may ask for
  less, never more; absence gets the ceiling, not "unbounded".
- `model` is unconditionally overwritten to the one served model name -
  not merely validated and rejected, since there is nothing ambiguous to
  reject when only one answer is ever correct.

This is server-side and unconditional, not a client-library convenience -
the whole point is that a caller cannot opt out of the parts that protect
the platform (2 and 3), while still being able to opt back into the parts
that are purely a taste default (1).

## Consequences

- This is the actual argument for having a gateway at all in front of an
  OpenAI-compatible server that a client could otherwise call directly -
  see docs/adr/0004. Without `policy.py`, the gateway would be a
  proxy with no reason to exist beyond auth.
- A caller inspecting the exact request vLLM received (e.g. via logs) will
  see a body that differs from what they sent - this is deliberate and
  documented here, not a bug to be surprised by.
- Future policy (per-tenant budgets, a semantic cache, a prompt guard) slots
  into this same module in M4 without changing the shape of `auth.py` or
  `upstream.py`.
