# -*- coding: utf-8 -*-
"""Content for the M4 engineering document."""
from docx_kit import *  # noqa: F403
from m0 import dual, _steps, _qa  # reuse the shared rendering helpers

SECTIONS = [
    "cover", "what_it_was_for", "starting_point", "decisions",
    "what_was_built", "how_it_was_done", "deep_dive", "deviations",
    "tool_choices", "limitations", "mistakes", "explain", "glossary_and_next",
]

REBUILD_RESULT = (
    "**Passed from a clean rebuild**, with two gaps the rebuild itself found and closed. "
    "`make down && make up && make gpu-check && make gitops` brought a brand-new cluster to all six "
    "Applications Synced + Healthy - policies, secrets, the palisade chart, the observability secret, "
    "and the observability stack itself, in that order. `tests/load/two-tenants.js` then passed for "
    "real against the rebuilt cluster, re-run a second time after a Redis restart for a clean budget "
    "state (tenant-a 100% success over 31 requests, tenant-b budget-exhausted 23 times) - "
    "`docs/evidence/m4/08-two-tenants-k6-run-post-rebuild.txt`. The rebuild was not hands-free the "
    "first time: `make up` hit a transient Docker network race right after `make down` and needed one "
    "manual retry, and a cluster left stopped by a prior session needed `k3d cluster start` by hand. "
    "Both are now in `scripts/cluster-up.sh` itself, per the project rule that a fix needed once belongs "
    "in the script, not in a person's memory of what to type"
)


# =============================================================================
def cover(D):
    d = D.d
    t = d.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade_cell(c, F_COVER); c.text = ""
    p = c.paragraphs[0]; no_space(p, 20, 2)
    r = p.add_run("PALISADE")
    r.bold = True; r.font.size = Pt(26); r.font.name = BODY_FONT; r.font.color.rgb = WHITE
    p2 = c.add_paragraph(); no_space(p2, 2, 2)
    r = p2.add_run("Engineering Log  ·  Milestone M4")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("Platform & Observability: who is using it, what it costs, and whether it's healthy")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M4 - Platform Features & Observability**"],
            ["Goal", "The platform becomes multi-tenant and legible - who is using it, what it costs, and "
                     "whether it is healthy"],
            ["Result", "**Passed.** Two tenants sent real traffic against the live cluster; tenant-b's "
                       "small budget was exhausted mid-run (22 `429 budget_exhausted` responses) while "
                       "tenant-a stayed at 100% success - recorded in `docs/evidence/m4/`"],
            ["Rebuild", REBUILD_RESULT],
            ["Gateway", "Redis-backed per-tenant rate limits and token budgets (atomic Lua reservation), a "
                       "response cache that still bills budget on a hit, a regex prompt guard, and a "
                       "structured audit log at every terminal outcome"],
            ["Observability", "Prometheus, Grafana, kube-state-metrics and an nvidia-smi GPU exporter - "
                              "four dashboards, five alert rules, deliberately decoupled from the core "
                              "workload chain"],
            ["New code", "`services/gateway/app/{tenancy,cache,guard}.py`, `deploy/charts/palisade` "
                         "(Redis), `deploy/observability{,-secrets}/`, `tests/load/two-tenants.js`, "
                         "ADRs 0021-0023"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("Same structure as M0-M3, answering the same six standing questions.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**", "§4 What was built and **§5 How it was done**"],
            ["**2. What was done differently**, and why", "**§7 Deviations**"],
            ["**3. How it was done**", "§5, plus **§6** - the GPU exporter bug a real pod exposed"],
            ["**4. What the limitations are**", "**§9 Limitations**"],
            ["**5. Why this tool/approach over the alternatives**", "**§8 Tool choices**, ADRs 0021-0023"],
            ["**6. Plain language and technical, both**", "Throughout, as **IN PLAIN LANGUAGE** / "
             "**TECHNICALLY** pairs"],
        ],
        widths=[2.1, 4.5],
    )
    D.callout("The one thing to take away from M4",
              "A metric that is merely collected can still lie. The cache had to be made to bill a "
              "tenant's budget on a hit, not just on a real generation, or the cost dashboard would show "
              "a customer's spend vanishing the moment their traffic got predictable - the opposite of "
              "what a cost-attribution dashboard exists to show.", "ok")


# =============================================================================
def what_it_was_for(D):
    D.h1("1. What M4 Was For")
    D.h2("1.1  The goal, stated simply")
    dual(D,
         "M3 made the cluster refuse anything it couldn't verify. M4 makes the platform answer three "
         "questions an operator actually needs answered: who is using it, what it costs, and whether it "
         "is healthy right now. Before M4, every API key had the same unlimited budget and nobody could "
         "see GPU load, spend per customer, or security events without reading pod logs by hand.",
         "Move tenant identity from a flat hash list to named tenants with a rate limit and a token "
         "budget each, backed by Redis for the mutable state (rate-limit windows, budget counters, a "
         "response cache). Add a regex-based input guard. Ship Prometheus, Grafana, kube-state-metrics "
         "and a GPU exporter as their own Argo CD-managed stack, with four dashboards and five alert "
         "rules.")
    D.h2("1.2  The acceptance test")
    D.table(
        ["Criterion (from the plan)", "How it was demonstrated", "Evidence"],
        [
            ["Two tenants show divergent spend on the dashboard", "tenant-a (50,000-token budget) and "
             "tenant-b (500-token budget) both sent real chat-completion traffic at a fixed 1 req/s for "
             "30s via `tests/load/two-tenants.js`", "`01-two-tenants-k6-run.txt`"],
            ["One hits its budget ceiling and receives 429 while the other is unaffected", "tenant-b: 22 "
             "`429 budget_exhausted` out of 31 requests. tenant-a: 100% success (30/30), real GPU latency "
             "up to 4.05s", "`01-two-tenants-k6-run.txt`"],
            ["(supporting) The dashboards and alerts are real, not decorative", "All five Prometheus "
             "scrape targets `up`; all four Grafana dashboards provisioned; "
             "`PalisadeTenantBudgetExhausted` fired live with the correct tenant label once triggered",
             "`02-observability-verification.txt`"],
        ],
        widths=[2.3, 3.5, 1.2],
        size=9.0,
    )
    D.callout("Why the cache mattered to the test, not just the budget",
              "A cache hit still costs nothing on the GPU - so a load test using one fixed prompt would "
              "cache-hit after the first call and never really exercise the budget path. "
              "`tests/load/two-tenants.js` puts the VU and iteration number into every prompt so each "
              "request is a real generation, and the gateway bills a cache hit's *actual* recorded usage "
              "to the tenant's budget regardless (ADR 0021) - so the acceptance test is honest either way.",
              "note")


# =============================================================================
def starting_point(D):
    D.h1("2. What Was True Going Into M4")
    D.table(
        ["Inherited from M3", "Consequence for M4"],
        [
            ["`auth.py` already returned a hash and said, verbatim, 'M4 moves the lookup to Redis'",
             "The literal reading would need a seeding mechanism and move tenant identity out of Git - "
             "the actual design keeps identity in config and only mutable state in Redis (ADR 0021)"],
            ["A `NetworkPolicy` already had an inert, unused rule for Redis on vLLM's gateway-only ingress",
             "Redis's own NetworkPolicy and the gateway's egress rule to it needed zero edits to the "
             "existing allow-gateway policy"],
            ["Kyverno's pod-security baseline was scoped to the `palisade` namespace only",
             "The new `monitoring` namespace's pods (Prometheus, Grafana, etc.) are outside what that "
             "policy enforces - hardened anyway, by choice, not by requirement"],
            ["`make up-full` existed, reserved for 'M4 observability', identical to `up-lite`",
             "A real RAM measurement (5.4 GiB used, 4.3 GiB free, inside the 9.7 GiB WSL2 cap) showed the "
             "whole stack fits under 1 GiB combined - the toggle the plan assumed turned out unnecessary"],
        ],
        widths=[3.0, 3.6],
    )


# =============================================================================
def decisions(D):
    D.h1("3. Decisions, With the Decision Records")
    D.table(
        ["ADR", "Decision", "In one line, why"],
        [
            ["0021", "Tenant identity/limits in config; rate-limit, budget and cache state in Redis",
             "Keeps tenant provisioning a Git commit (GitOps posture) while giving the mutable, "
             "per-request state a race-safe, shared store"],
            ["0022", "Prompt guard: regex heuristics, not a model call", "A second generation per request "
             "would roughly double GPU time on hardware that's already the tightest constraint, for a "
             "guard with no evaluated accuracy yet"],
            ["0023", "Plain manifests for Prometheus/Grafana, no Operator, no Alertmanager, decoupled "
             "sync-wave", "Four small Deployments beat one Operator's CRDs for four fixed, known targets; "
             "a stalled dashboard image must never block the gateway"],
        ],
        widths=[0.5, 2.6, 3.5],
        size=9.2,
    )


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")
    D.h2("4.1  The request path, extended")
    D.code(
        "POST /v1/chat/completions\n"
        "  1. rate limit     tenancy.TenantStore.check_rate_limit  - sliding window, Lua script\n"
        "  2. input guard    guard.apply_guard  - length / injection reject, PII redact\n"
        "  3. budget reserve tenancy.TenantStore.reserve_budget    - atomic INCRBY + check, Lua script\n"
        "  4. cache lookup   cache.ResponseCache.get  - keyed on tenant + model + messages + params\n"
        "  5. upstream call  (only on a cache miss) - vLLM, with X-Request-ID forwarded\n"
        "  6. reconcile      adjust_budget(actual - reservation); bill tenant_tokens_total\n"
        "  7. audit line     one structured log event, tenant + outcome + tokens, never prompt content")
    D.h2("4.2  The pieces")
    D.table(
        ["Component", "What it does", "Where"],
        [
            ["TenantStore", "Two Lua scripts: atomic budget reservation (with TTL self-repair) and "
             "sliding-window rate limiting via a sorted set", "`app/tenancy.py`"],
            ["ResponseCache", "Per-tenant-keyed cache; a hit still bills the tenant's real recorded usage",
             "`app/cache.py`"],
            ["Prompt guard", "Length clamp, injection regexes, PII redaction (email/SSN/credit-card "
             "shaped) - each outcome a labelled metric", "`app/guard.py`"],
            ["Audit logging", "One `chat_completion_settled` event per request, at every terminal point "
             "including rejections - tenant, outcome, status, token counts, duration; never the prompt",
             "`app/routes/chat.py`"],
            ["Redis", "Backs all of the above; no PVC (in-memory only, ADR 0023's reasoning applies "
             "here too)", "`deploy/charts/palisade/templates/redis-*.yaml`"],
            ["Prometheus", "Five static scrape targets: gateway, vLLM, kube-state-metrics, GPU exporter, "
             "Kyverno; five alert rules", "`deploy/observability/prometheus*.yaml`"],
            ["Grafana", "Four dashboards, file-provisioned from ConfigMaps so every panel is a diffable "
             "file in Git", "`deploy/observability/grafana*.yaml`"],
            ["kube-state-metrics", "Narrow ClusterRole (`pods` only) - feeds the restart-loop alert",
             "`deploy/observability/kube-state-metrics.yaml`"],
            ["GPU exporter", "Project-built; wraps `nvidia-smi`, the only option that works under WSL2's "
             "NVML gap (ADR 0002/0023) - took two fixes to get real data out of it, §6",
             "`docker/gpu-exporter/`, `deploy/observability/gpu-exporter.yaml`"],
        ],
        widths=[1.3, 3.6, 1.7],
        size=9.0,
    )
    D.h2("4.3  The four dashboards")
    D.table(
        ["Dashboard", "What it answers"],
        [
            ["SLO", "Request rate by status, chat-completion error rate, p95 latency, p95 time-to-first-"
             "token"],
            ["GPU & Model", "GPU utilisation / VRAM (nvidia-smi - see §6), vLLM's own queue depth, "
             "completion tokens/sec"],
            ["Cost & Tenancy", "Tokens/sec by tenant, budget remaining by tenant, budget-exhausted "
             "rejections by tenant, cache hit rate, tokens saved by the cache"],
            ["Security", "Auth failures by reason, prompt-guard blocks by reason, rate-limited requests "
             "by tenant, Kyverno admission denials by rule"],
        ],
        widths=[1.3, 5.3],
    )
    D.h2("4.4  The alert rules")
    D.table(
        ["Alert", "Fires when"],
        [
            ["PalisadeSLOBurnRateHigh", "Chat-completion 5xx rate over 5%, sustained `for: 5m`"],
            ["PalisadeGPUSaturated", "GPU utilisation over 95%, sustained `for: 10m`"],
            ["PalisadeTenantBudgetExhausted", "`increase(...[5m]) > 0` on budget-exhausted rejections - "
             "**confirmed firing live**, §6 and `docs/evidence/m4/`"],
            ["PalisadeInjectionBlockSpike", "More than 5 suspected prompt-injection attempts, `increase(...[5m])`"],
            ["PalisadeRestartLoop", "Any `palisade` namespace pod restarts more than 3 times, `increase(...[15m])`"],
        ],
        widths=[2.1, 4.5],
        size=9.2,
    )


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done")
    _steps(D, [
        ("Gateway features built and unit-tested before touching the cluster",
         "`tenancy.py`'s two Lua scripts, `cache.py`, `guard.py`, and `chat.py`'s rewritten request "
         "pipeline, all developed against `fakeredis` (with the `lua` extra, so the scripts themselves "
         "run under test, not just mocked around) - 48 tests passing before any image was built."),
        ("A pre-existing bug found and fixed in the same pass",
         "The streaming path's `finally` block incremented `status=\"200\"` on every request regardless "
         "of the actual outcome - every streaming error was also counted as a success. Fixed by tracking "
         "the real status in a variable and incrementing once."),
        ("Infra built as plain manifests, validated before any cluster touched them",
         "`helm template` plus `kubectl apply --dry-run` for the chart's Redis addition; `promtool check "
         "rules`/`check config` for syntax, then `promtool test rules` (`tests/prometheus/`) against "
         "synthetic input series for every rule's actual firing behaviour; each dashboard JSON parsed to "
         "confirm it was valid before it ever reached Grafana."),
        ("A real bug in the secrets mechanism, found before it shipped",
         "The sops-decrypt CMP's `generate` command concatenates every `*.yaml` file in a source "
         "directory with no document separator - safe for one file, broken for twelve. Caught by "
         "simulating the plugin's exact shell command against both directories before committing, not by "
         "a failed sync. Fixed by giving the one encrypted file its own single-file directory and Argo CD "
         "Application (`palisade-observability-secrets`) rather than trying to patch the plugin."),
        ("CI caught a real, unrelated CVE on the first push",
         "Trivy failed the build on a new HIGH finding in `libpcre2` - a base-image package, not anything "
         "M4 touched. Bumped `python:3.12-slim`'s pinned digest to its current build (checked against "
         "Docker Hub's tags API, scanned locally with `trivy` before pushing again); the newer build also "
         "incidentally cleared two `openssl` CVEs that had been accepted-risk entries since M2."),
        ("Live verification, not just a green pipeline",
         "After the bump-digest PR merged: a full `make down && make up && make gitops` clean rebuild; "
         "`tests/load/two-tenants.js` run for real against the rebuilt cluster with the two SOPS-encrypted "
         "demo keys; every Prometheus target and Grafana dashboard checked by hand; one alert "
         "(`PalisadeTenantBudgetExhausted`) deliberately triggered and confirmed firing."),
        ("A second pass found four more gaps a first pass at 'done' had missed",
         "The streaming path (M1's actual request shape) had never been exercised live - sent one for "
         "real, read the audit line, both token counts non-zero and correct "
         "(`docs/evidence/m4/07-streaming-live.txt`). Kyverno's signature policy covered the gateway and "
         "model-verify but not the gpu-exporter image, in a different namespace - added a third rule, "
         "confirmed the real signed image still gets admitted after a rollout restart. The Cost "
         "dashboard was missing the one panel the plan explicitly promised ('tokens saved measured'). "
         "And `promtool test rules` had no way to run itself - added `make test-alert-rules` and a CI "
         "job that needs no cluster."),
    ])
    D.h2("5.1  The commands that matter")
    D.code(
        "make down && make up && make gpu-check && make gitops   # clean rebuild, M0-M4 all Synced/Healthy\n"
        "kubectl -n palisade port-forward svc/palisade-gateway 18080:8080 &\n"
        "PALISADE_TENANT_A_KEY=... PALISADE_TENANT_B_KEY=... k6 run tests/load/two-tenants.js\n"
        "kubectl -n argocd get applications          # six, all Synced / Healthy\n"
        "curl .../api/v1/targets | jq '.data.activeTargets[].health'   # five x \"up\"")


# =============================================================================
def deep_dive(D):
    D.h1("6. Deep Dive - Two Bugs Behind One Empty Dashboard Panel")
    dual(D,
         "A small metrics-collecting program ran perfectly well and still produced no GPU numbers at "
         "all. It calls the same `nvidia-smi` tool that works everywhere else in this project. Two "
         "separate things were wrong with it, and fixing only the first one - which looked like the "
         "whole story - still wasn't enough.",
         "First: `utkuozdemir/nvidia_gpu_exporter` ships no shell and no `/usr/bin` at all - confirmed "
         "directly, even `docker run --entrypoint ls` fails. CDI's injection hook places `nvidia-smi` by "
         "symlinking it into `/usr/bin`, which had nowhere to land. Rebuilding on `python:3.12-slim` (the "
         "same base already trusted for the gateway) gave it a normal filesystem - and `nvidia-smi` was "
         "*still* missing. Diffing against the known-working `gpu-check` Job "
         "(`nvidia/cuda:12.8.1-base-ubuntu24.04`) found the second bug: that image sets "
         "`NVIDIA_DRIVER_CAPABILITIES` by default, and nothing else in this project did. "
         "`nvidia-container-runtime`'s CDI hook only injects the \"utility\" capability - the one that "
         "carries `nvidia-smi` and the NVML libraries - when that variable asks for it.")
    D.h2("What was tried, in order")
    D.table(
        ["Attempt", "Result"],
        [
            ["Confirm the pod is actually CDI-wired (`runtimeClassName: nvidia`, the annotation)",
             "Both present and correct - identical to vLLM's own, which works"],
            ["Exec into the pod and look for `nvidia-smi` or any shell", "Neither exists; even `ls` fails"],
            ["Rebuild on a full-filesystem base image (`python:3.12-slim`)", "Necessary, not sufficient - "
             "`nvidia-smi` was still missing after this alone"],
            ["Diff against `k8s/gpu-check.yaml` (known working) for anything the two images set "
             "differently", "`nvidia/cuda`-based images default `NVIDIA_DRIVER_CAPABILITIES`; this one "
             "never had it set"],
            ["Set `NVIDIA_VISIBLE_DEVICES=all` + `NVIDIA_DRIVER_CAPABILITIES=utility` on a scratch pod, "
             "no rebuild yet", "`/usr/bin/nvidia-smi` appeared immediately, and ran for real against the "
             "RTX 3050"],
            ["Bake both ENV lines into the image itself; rebuild; re-verify end to end including the "
             "exporter's own `/metrics`", "Confirmed - real utilisation, VRAM and temperature numbers, "
             "`docs/evidence/m4/04-gpu-exporter-fixed.txt`"],
        ],
        widths=[2.8, 3.8],
        size=8.8,
    )
    D.p("The whole investigation ran as scratch pods against the live cluster - zero cost (no CI run, no "
        "image push, no PR), and immune to Argo CD's self-heal reverting an unreviewed change mid-test, "
        "the same technique this project has used since the M3 signature-verification investigation. "
        "Only once the fix was proven live did it become `docker/gpu-exporter/`'s actual Dockerfile and "
        "its own signed CI pipeline (`gpu-exporter-image.yml`), replacing the third-party image entirely.")
    D.callout("Lesson",
              "A healthy readiness probe proves the HTTP server started, not that the thing it's supposed "
              "to measure actually works - `nvidia_smi_last_collect_success` was the number that told the "
              "truth, checked by hand. And a plausible first fix can still be wrong: the full-filesystem "
              "rebuild was real progress and still left the exporter blind, because it was never the only "
              "thing broken.", "warn")


# =============================================================================
def deviations(D):
    D.h1("7. Deviations From the Plan")
    D.table(
        ["Plan said", "What was done", "Why"],
        [
            ["'M4 moves the lookup to Redis' (auth.py's own M1 comment)", "Tenant identity/limits stayed "
             "in config (now a richer `PALISADE_TENANTS` secret); only rate-limit, budget and cache state "
             "moved to Redis", "Moving identity itself would need a seeding mechanism and take tenant "
             "provisioning out of Git - a worse fit for this project's GitOps posture (ADR 0021)"],
            ["Observability only when working on it (`up-full` toggle)", "Deployed unconditionally via "
             "its own always-synced Argo CD Application", "A real RAM measurement showed the whole stack "
             "fits in under 1 GiB of the 4.3 GiB that was free - the toggle the plan assumed turned out "
             "unneeded (ADR 0023)"],
            ["(implicit) kube-prometheus-stack or similar", "Four hand-written Deployments plus "
             "ConfigMaps, no Operator, no Alertmanager", "Four fixed, known scrape targets don't need an "
             "Operator's CRDs; no real alert receiver exists yet for Alertmanager to route to (ADR 0023)"],
            ["(not in plan) the sops-decrypt CMP concatenation bug", "The observability stack's one "
             "secret split into its own single-file directory and Application", "Found by simulating the "
             "plugin's exact shell command before committing - a directory with more than one YAML file "
             "was never safe to decrypt through it, and nothing had tripped over this before M4"],
            ["(not in plan) trust a third-party GPU exporter image", "Built, scanned, signed and pushed "
             "the project's own (`docker/gpu-exporter/`, `gpu-exporter-image.yml`), replacing it entirely",
             "The third-party image's minimal filesystem and missing `NVIDIA_DRIVER_CAPABILITIES` left it "
             "unable to run `nvidia-smi` at all (§6) - fixing it meant owning the image"],
        ],
        widths=[1.9, 2.3, 2.4],
        size=9.0,
    )


# =============================================================================
def tool_choices(D):
    D.h1("8. Tool Choices - and What Was Rejected")
    D.table(
        ["Chose", "Over", "Because"],
        [
            ["**Redis**", "In-process memory per replica", "Rate limits and budgets must be race-safe "
             "and shared if the gateway ever runs more than one replica - Lua scripts, not a plain "
             "read-then-write"],
            ["Regex/keyword prompt guard", "A model-based classifier", "A second generation per request "
             "roughly doubles GPU time on the tightest resource this project has, for an unevaluated "
             "accuracy gain (ADR 0022)"],
            ["**Plain manifests**", "`kube-prometheus-stack`", "No Operator/CRDs for four fixed targets; "
             "every dashboard and alert rule stays a diffable file, not a Helm value (ADR 0023)"],
            ["`nvidia-smi` CLI wrapper, project-built", "`dcgm-exporter` / NVML-based tools, and the "
             "third-party exporter first tried", "NVML doesn't work under WSL2 (ADR 0002) regardless of "
             "which tool calls it; the third-party image's own filesystem and missing driver-capability "
             "env var made it unfixable from the outside (§6)"],
            ["No Alertmanager", "Deploying it anyway, unused", "Running a notification pipeline with no "
             "real receiver configured would be theatre, not infrastructure"],
            ["Static Prometheus scrape targets", "Kubernetes service discovery", "Five fixed targets "
             "never change shape; `kubernetes_sd_configs` would need Prometheus to hold a cluster-wide "
             "ClusterRole for a convenience this cluster doesn't need"],
        ],
        widths=[1.7, 1.9, 3.0],
        size=9.0,
    )


# =============================================================================
def limitations(D):
    D.h1("9. Limitations")
    D.p("What this setup genuinely cannot do, stated plainly.")
    D.table(
        ["Limitation", "Why it exists / what would fix it"],
        [
            ["`estimate_tokens` is a rough pre-flight guard, not a guaranteed overestimate",
             "Counts characters, not real tokens - a prompt denser than the assumed chars-per-token can "
             "under-reserve, and the uncapped `INCRBY` lets a tenant end a window slightly over its "
             "nominal budget. Closing this exactly needs vLLM's own tokenizer"],
            ["No Alertmanager - no deduplication, grouping or routing",
             "Five rules firing at once produce five separate alert states in Prometheus, not one "
             "notification. Acceptable with no real receiver to route to yet"],
            ["Tenant revocation needs a gateway restart to take effect",
             "`PALISADE_TENANTS` is read once at startup - a deliberate trade for keeping tenant identity "
             "in Git rather than in Redis (ADR 0021)"],
            ["Redis has no PersistentVolumeClaim", "A Pod reschedule (node drain, eviction, deliberate "
             "deletion) gets a genuinely empty store; a container restarting in place within the same Pod "
             "does not, since the stock image's own periodic snapshot plus the surviving emptyDir reload "
             "recent state - confirmed live in M5's chaos testing. Acceptable either way for a "
             "portfolio-scale platform; would need a PVC (and the sync-wave care ADR 0017 already paid "
             "for vLLM's cache) to make both cases stateless"],
            ["The prompt guard is keyword/regex-based", "Catches the textbook injection phrasing and "
             "nothing subtler - defence in depth, one layer among several, not a claim that prompt "
             "injection is solved (ADR 0022)"],
            ["The gpu-exporter Kyverno rule has no tampered-image negative control",
             "The gateway and model-verify rules each have one (M3's own evidence) proving the same "
             "verification code path denies an unsigned image; this third rule uses that identical path "
             "with a different `imageReferences` pattern. A real attempt was made and stopped when "
             "`gh auth token` turned out not to carry `packages:write` - the same class of scope gap M2 "
             "hit with the `workflow` scope, not chased further here"],
        ],
        widths=[2.6, 4.0],
        size=9.0,
    )


# =============================================================================
def mistakes(D):
    D.h1("10. Mistakes and What They Taught")
    D.table(
        ["Mistake", "Lesson"],
        [
            ["Shipped the first version of the tenant-budget Lua script setting a TTL only on what it "
             "assumed was the first write", "`adjust_budget`'s own `INCRBY` can recreate a key with no "
             "expiry if it ever lapses between a reservation and its reconciliation - check the actual "
             "TTL on every write, not a proxy for 'is this the first one'"],
            ["Let a streaming response's token count silently stop feeding the platform-wide "
             "`tokens_total` metric during a refactor", "A metric with no test watching it can regress "
             "invisibly - added a streaming test that asserts the reconciled count, not just that the "
             "chunks relay in order"],
            ["Assumed a cache would naturally keep costing a tenant nothing on a hit",
             "That's backwards for a cost-attribution dashboard - a hit has to bill the tenant's real "
             "recorded usage or the dashboard would show spend vanishing exactly when traffic gets "
             "predictable"],
            ["Put the observability stack's one encrypted secret in the same directory as eleven plain "
             "manifests", "The sops-decrypt CMP concatenates every file in a source path with no "
             "separator - caught by simulating its exact command before committing, not by a failed sync"],
            ["Trusted a third-party exporter image without checking its filesystem or its "
             "NVIDIA_DRIVER_CAPABILITIES setting first", "Found both problems only after a dashboard "
             "panel came back empty, the expensive order - checking a GPU image's filesystem and driver-"
             "capability env var up front is cheap; debugging a silent CDI no-op after the fact is not"],
        ],
        widths=[2.9, 3.7],
    )


# =============================================================================
def explain(D):
    D.h1("11. Design Rationale - Questions Answered")
    _qa(D, [
        ("Why Lua scripts instead of a simple INCR and a check in Python?",
         "Two concurrent requests from the same tenant could both read 'under budget' before either "
         "writes. A single atomic script closes that race; two round-trips to Redis from Python cannot."),
        ("Why does a cache hit still cost the tenant tokens?",
         "Because the cost-attribution dashboard exists to show real spend. If a cache hit were free, a "
         "tenant sending repetitive traffic would appear to stop costing anything the moment their "
         "pattern became predictable - exactly backwards."),
        ("Why not use the full kube-prometheus-stack chart? Everyone does.",
         "Everyone's cluster usually has more than four scrape targets and more than one dashboard "
         "consumer. This one has neither, and the Operator's CRDs and node-exporter's host access would "
         "cost more than they'd save here."),
        ("Why does the observability stack get to fail without blocking the gateway, but secrets don't?",
         "Secrets are load-bearing - the gateway can't authenticate anyone without them, so blocking is "
         "the point (ADR 0020). A stalled Grafana image pull has no equivalent claim on the workload's "
         "correctness."),
        ("What would you change starting over?",
         "Simulate the sops-decrypt CMP's exact shell command against any new secrets directory before "
         "writing a single manifest for it, and check a third-party image's filesystem and its "
         "NVIDIA_DRIVER_CAPABILITIES before trusting it in a GPU pod, not after a dashboard panel comes "
         "back empty."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("12. Glossary - Terms Introduced in M4")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**Token budget**", "A cap on how many tokens a tenant may consume in a rolling time window, "
             "enforced before the GPU is touched"],
            ["**Sliding-window rate limit**", "Counts requests in the last N seconds exactly, using a "
             "sorted set of timestamps, rather than resetting a counter at fixed clock boundaries"],
            ["**Lua script (Redis)**", "A small program Redis runs atomically, server-side - the only way "
             "to make a check-then-write race-safe without a second round trip"],
            ["**Prompt guard**", "A filter that inspects a request before it reaches the model - here, "
             "length, injection phrasing, and PII"],
            ["**Scrape target**", "A URL Prometheus polls on a schedule for metrics in its text format"],
            ["**CDI (Container Device Interface)**", "The mechanism that injects a GPU (and the binaries/"
             "libraries that talk to it) into a container, used throughout this project since the NVIDIA "
             "device plugin cannot work under WSL2"],
            ["**Alertmanager**", "Prometheus's companion for deduplicating, grouping and routing firing "
             "alerts to a real notification channel - not deployed here (ADR 0023)"],
        ],
        widths=[1.7, 4.9],
        size=9.3,
    )
    D.h1("13. Open Items Going Into M5")
    D.table(
        ["Item", "Action"],
        [
            ["No Alertmanager receiver", "Wire one once there's a real notification channel to use"],
            ["estimate_tokens can under-reserve", "A real tokenizer would close the gap exactly"],
        ],
        widths=[2.6, 4.0],
    )
    D.spacer(4)
    D.callout("Where M5 goes",
              "**M5 - Resilience, proof and storytelling.** A load test to saturation, a deliberate chaos "
              "day, and the write-up that turns a working system into a case for hiring the person who "
              "built it: the threat model, the SLO backed by real numbers, the runbook, the postmortem.",
              "ok")
