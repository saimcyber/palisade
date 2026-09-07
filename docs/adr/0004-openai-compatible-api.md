# 4. OpenAI-compatible API surface

- **Status:** Accepted

## Context

The gateway needs a request/response shape. It could invent its own, or
match an existing one. vLLM itself already exposes an OpenAI-compatible
server, which made the second option close to free.

## Decision

The gateway's public surface (`/v1/models`, `/v1/chat/completions`, request
and response bodies, SSE chunk format) matches the OpenAI Chat Completions
API. This is a strategic choice, not a cosmetic one: it is the de facto
standard that every mainstream client library, eval harness, and LLM tool
(LangChain, the `openai` Python/JS SDKs, most benchmarking suites) already
speaks. A caller can point at this gateway by changing a base URL and an
API key - nothing else. Palisade does not have to build or document a
client library, a request/response reference, or SDK bindings; that surface
already exists and is already documented, elsewhere, by someone else.

## Consequences

- The gateway's job becomes translation and policy enforcement at a
  well-known boundary, not API design - `policy.py`'s job (injecting
  `enable_thinking: false`, clamping `max_tokens`, pinning the model name)
  is legible to anyone who already knows the OpenAI API, without reading
  Palisade's own docs first.
- Constrains the gateway: it cannot add a field or behaviour that breaks a
  client's expectation of what "OpenAI-shaped" means without that being a
  compatibility regression, not just an internal API change.
- Vendor-neutral in a specific sense: matching an API is not the same as
  depending on OpenAI's service. Nothing here calls OpenAI; vLLM (M1) or
  any future backend implementing the same surface can sit behind the
  gateway unchanged.
