# 25. The saturation load test runs in CI against a stub, and for real on the GPU locally - never a self-hosted runner

- **Status:** Accepted

## Context

The plan calls for a k6 load test "ramping to saturation, run in CI."
This repository is public, and GitHub Actions only gives public repos a
GPU-capable, self-hosted runner if the repository owner registers one -
pointing GitHub Actions at this laptop's own GPU.

## Decision

**No self-hosted runner, on this or any future public repository of
this project.** A self-hosted runner attached to a public repo executes
whatever workflow YAML a pull request brings with it - including a
fork's pull request, by default, unless `pull_request_target` or an
approval gate is added correctly everywhere, which is exactly the kind
of security-critical configuration that is easy to get subtly wrong once
and catastrophic to get wrong even once. The result would be: anyone who
opens a PR against this repository can run arbitrary code on the laptop
that also holds the SOPS age key, the model-verify signing identity's
trust, and this project's own GitHub OIDC-federated AWS access. That is
not a risk this project's threat model (`docs/THREAT-MODEL.md`) accepts
for the sake of one load-test job running on managed infrastructure
instead of a free one.

**What actually runs where:**

- **In CI** (`alert-rules-test.yml`'s sibling, the load-test workflow):
  k6 runs the real `tests/load/two-tenants.js` and a new saturation
  script against the gateway with a **stub upstream** - a tiny mock HTTP
  server standing in for vLLM, returning a fixed completion instantly.
  This exercises every line of the gateway's own logic under real
  concurrent load - rate limiting, budget reservation, the cache, and
  **the load shedding ADR 0024 just added** - on infrastructure GitHub
  owns, with no GPU and no laptop involved.
- **Locally, for real**: the same saturation script run against the
  actual RTX 3050 and actual vLLM, by hand, on this laptop, with the
  results captured as evidence (`docs/evidence/m5/`) and the numbers
  that back `docs/SLO.md`. This is the only run that can answer "what
  does this hardware's real ceiling look like," and it is deliberately
  never automated into a workflow that a stranger's pull request could
  trigger.

## Consequences

- CI's run proves the gateway's *logic* holds under concurrency (no
  race in the Lua scripts, no leaked in-flight slots, the cache doesn't
  corrupt under contention) - it says nothing about GPU throughput,
  tokens/sec, or real latency. Both numbers matter; neither substitutes
  for the other, and this ADR is the record of why they're measured in
  two different places on purpose.
- A contributor's PR that changes gateway logic gets the concurrency
  check automatically. A contributor's PR that claims to improve GPU
  throughput gets no automatic verification at all - that has to be
  taken on trust or re-measured locally by a maintainer, same as this
  project's own GPU acceptance tests (`make gpu-check`) already are.
- If this project ever moves off a laptop GPU onto a cloud one with a
  real managed-runner budget, this decision is the first thing to
  revisit - the constraint here is specifically "this is a personal
  laptop holding real signing material," not "GPU runners are
  categorically unsafe."
