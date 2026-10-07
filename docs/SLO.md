# Service Level Objectives

Targets set from measured numbers, not picked first and hoped for -
every number below has an evidence file behind it.

## What's actually being promised

This is a single-replica, single-GPU, no-autoscaling model tier (ADR
0005) on a laptop. The honest SLO for a system like this isn't "always
fast" - it's **"never silently wrong, and degrade on purpose before you
degrade by accident."** Every target below reflects that.

## SLIs and targets

| SLI | Target | Measured | Evidence |
| --- | --- | --- | --- |
| **Correctness rate**: fraction of requests that get either a correct answer or a deliberate, labelled rejection (never a bare `5xx`, never a hang) | 100% | **100%** - 0 genuine server errors across 20,113 requests under a 30-VU flood | `docs/evidence/m5/01-saturation-real-gpu.txt` |
| **p95 latency, served request, light load** (1 req/s/tenant, ≤32 tokens) | < 2s | **1.73s** (p95), avg 674ms | `docs/evidence/m4/08-two-tenants-k6-run-post-rebuild.txt` |
| **p95 latency, served request, under saturation** (30 VUs flooding, 16 tokens) | < 1s - admitted traffic should stay fast precisely *because* shedding keeps it from queueing | **626ms** (p95), max 672ms | `docs/evidence/m5/01-saturation-real-gpu.txt` |
| **Tenant isolation**: one tenant exhausting its budget must not affect another's success rate | Unaffected tenant stays ≥ 99% success | **100%** (31/31, then 30/30) across two independent runs | `docs/evidence/m4/01-*`, `08-*` |
| **Time to first token** (streaming) | Measured, not yet targeted - no live number existed before M5 | p50 ≈ sub-second on first real streaming test (see below) | `docs/evidence/m4/07-streaming-live.txt` |
| **Admission correctness**: an unsigned/tampered image is refused, never silently admitted | 100% | **100%**, with a positive control (identical spec, differing only in signature) proving the rule isn't just failing closed on everything | `docs/evidence/m3/03-*`, `docs/evidence/m4/06-*` |

## Error budget

Classic SRE error budgets (the "three nines" framing) assume "down" is
the failure mode worth budgeting. Here, the interesting failure modes
are different, so the budget is stated differently:

- **Zero budget for genuine server errors** (`5xx` other than the
  deliberate `503` load-shed response). A `500` means something broke;
  a `503` means something worked as designed. Conflating the two in one
  "error rate" number would hide the actual signal - this project keeps
  them separate everywhere (metrics, alerts, this document).
- **No budget on correctness of rejection reasons.** A `429` must say
  `rate_limited` or `budget_exhausted`, never a generic message - every
  rejection in `chat.py` is a named outcome, audited.
- **Full budget on raw throughput/latency under saturation**, because
  that's not what this platform is promising. It promises *honest,
  fast failure* under saturation, not infinite capacity. The 30-VU
  saturation run's 99.78% rejection rate is not a budget violation -
  it's the system doing exactly what ADR 0024 asked of it.

## What the real numbers revealed that the design didn't anticipate

The saturation test was built to isolate load shedding specifically.
Run for real against the actual tenant configuration, it mostly
exercised the **rate limiter** instead - 20,037 of 20,113 rejections
were `429`, not `503`, because 30 VUs flooding a tenant whose
configured limit is 120 req/min trips the rate limiter almost
immediately, long before the in-flight ceiling of 8 concurrent upstream
calls would matter. Load shedding still caught the 76 requests that got
past the rate limiter. This is arguably a *better* result than a clean
isolated signal would have been: it shows two independent defences
engaging in the correct order, under real conditions, with neither
masking a gap in the other. (The CI run against the stub upstream,
`.github/workflows/load-test.yml`, uses a tenant with a deliberately
generous rate limit specifically to isolate load shedding on its own -
see that workflow's own comment for why the two tests are allowed to
disagree about which control dominates.)

## Open items

- No SLO yet exists for sustained throughput (tokens/sec at steady
  state) - the saturation run measured latency under a flood, not a
  calibrated steady-state ceiling. A longer, steady-ramp test (not a
  sharp 30-VU spike) would be the next instrument to build.
- `max_in_flight_upstream_requests` (default 8, ADR 0024) was never
  recalibrated against a measurement - it's still the original guess.
