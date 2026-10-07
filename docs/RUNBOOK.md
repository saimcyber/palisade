# Runbook

One entry per alert that actually exists (`deploy/observability/prometheus-config.yaml`).
No speculative entries for alerts that don't exist yet - a runbook
entry for an alert nobody wrote is a lie waiting to be found during an
actual incident.

---

## PalisadeSLOBurnRateHigh

**Fires when:** chat-completion `5xx` rate exceeds 5%, sustained `for: 5m`.

**What it means:** Requests are failing for real (not a deliberate
`429`/`503`) - something in the gateway, Redis, or vLLM is actually
broken.

**First checks:**
1. `kubectl logs -n palisade deploy/palisade-gateway --tail=50` - look
   for `outcome: "upstream_error"` in the `chat_completion_settled`
   lines and read the `status` field.
2. `kubectl get pods -n palisade` - is vLLM `Running` and `1/1`? A
   crashed or restarting vLLM pod is the most likely cause.
3. `kubectl exec -n palisade deploy/palisade-gateway -- curl -s
   http://localhost:8080/readyz` - if this returns `503`, check whether
   it's vLLM or Redis that's unreachable (the response body says which).

**Likely fix:** If vLLM crashed, let it restart (`kubectl get pods -w`)
and confirm `/readyz` recovers once it does. If Redis is unreachable,
see `PalisadeTenantBudgetExhausted`'s Redis-specific checks below - the
same connectivity problem triggers both.

---

## PalisadeGPUSaturated

**Fires when:** `nvidia_smi_utilization_gpu_ratio` exceeds 95%,
sustained `for: 10m`.

**What it means:** The GPU is genuinely busy, not necessarily a
problem by itself - check whether requests are still being served
correctly before assuming this needs intervention.

**First checks:**
1. Check the GPU & Model dashboard's queue-depth panel
   (`vllm:num_requests_waiting`) - a growing queue alongside high
   utilisation means demand is outpacing capacity, which is exactly
   what `PalisadeLoadShedding` (below) exists to handle gracefully.
2. Check `palisade_load_shed_total` is actually incrementing. If GPU
   utilisation is high but nothing is being shed, the in-flight ceiling
   (`max_in_flight_upstream_requests`, default 8) may be set too high
   for what this GPU can actually sustain.

**Likely fix:** This is expected behaviour under real load, not an
incident on its own - the system is designed to shed before this
becomes a correctness problem. If it's sustained and legitimate, the
next step is lowering `max_in_flight_upstream_requests` (ADR 0024) so
shedding engages earlier, protecting latency for admitted requests at
the cost of admitting fewer.

---

## PalisadeTenantBudgetExhausted

**Fires when:** `increase(palisade_budget_rejected_total[5m]) > 0`.

**What it means:** A tenant hit its configured token budget - this is
**working as designed**, not an incident. Confirmed firing live for
real during M4's acceptance test (`docs/evidence/m4/02-*`).

**First checks:**
1. The alert's `tenant` label names who. Check the Cost & Tenancy
   dashboard's "budget remaining by tenant" panel to confirm it's
   genuinely at zero, not a metric lag artefact.
2. If this fires for a tenant whose budget *shouldn't* be exhausted
   (wrong tenant, unexpectedly low configured budget), check
   `PALISADE_TENANTS` in the gateway's Secret
   (`deploy/secrets/gateway-secret.enc.yaml`) for a misconfigured value.

**Likely fix:** If the budget is correctly exhausted and the tenant
needs more, that's a SOPS-encrypted secret edit and a redeploy - not a
live, hot-reloadable change (ADR 0021's stated limitation: tenant
config is read once at startup).

---

## PalisadeInjectionBlockSpike

**Fires when:** more than 5 suspected prompt-injection attempts in 5
minutes (`palisade_prompt_guard_blocks_total{reason="injection_suspected"}`).

**What it means:** Either a real attacker is probing the gateway, or a
legitimate integration is sending prompts that happen to match the
guard's coarse regexes (ADR 0022 - it's deliberately keyword-based and
can false-positive on legitimate text that resembles the textbook
injection phrasing).

**First checks:**
1. Check the Security dashboard's "prompt-guard blocks by reason" panel
   for which tenant and how concentrated in time the spike is.
2. The gateway's audit log never contains prompt content (by design,
   ADR 0022/`tests/test_privacy.py`) - there is no way to inspect *what*
   was blocked from inside this project's own logging. If root-causing
   a false positive requires seeing the actual text, that has to come
   from the caller's own side, not this platform's logs.

**Likely fix:** If it's a real attack, no action is needed beyond
confirming the guard is actually blocking (it is, by construction - a
block is what triggered the alert). If it's a false positive from a
legitimate integration, the regex in `app/guard.py` needs narrowing -
a code change, not a runtime config change.

---

## PalisadeRestartLoop

**Fires when:** any `palisade` namespace pod restarts more than 3 times
in 15 minutes.

**What it means:** Something is crash-looping - most likely vLLM (OOM,
bad weights) or the gateway (unhandled exception, bad config).

**First checks:**
1. `kubectl get pods -n palisade` - which pod, and what's its restart
   count.
2. `kubectl logs -n palisade <pod> --previous` - the crashed instance's
   last log lines, not the new one's.
3. If it's vLLM: check for `torch.OutOfMemoryError` specifically (see
   CLAUDE.md's GPU gotchas - this has a known history on this
   hardware).

**Likely fix:** Depends entirely on the crash reason found above. A
genuine VRAM exhaustion is covered by `docs/POSTMORTEM-001.md`'s
chaos-day finding.

---

## PalisadeLoadShedding

**Fires when:** `increase(palisade_load_shed_total[5m]) > 0`.

**What it means:** The gateway is deliberately refusing requests with
`503` because too many are already in flight to vLLM - this is the
system protecting itself, working as designed (ADR 0024), confirmed
live under real saturation (`docs/evidence/m5/01-*`).

**First checks:**
1. Is this expected (a real traffic spike, or an intentional load test)
   or unexpected (normal-looking traffic volume triggering it)? Check
   the SLO dashboard's "in-flight requests vs. the shed ceiling" panel.
2. If it's firing under normal traffic, the ceiling
   (`max_in_flight_upstream_requests`, default 8) may be set too low
   for what this hardware can actually sustain - cross-check against
   `docs/SLO.md`'s saturation numbers.

**Likely fix:** No action needed if this is genuinely protecting the
system under real saturation - that's the intended behaviour. If it's
firing too eagerly, raise `max_in_flight_upstream_requests` and
re-measure with `tests/load/saturation.js`, not by guessing.
