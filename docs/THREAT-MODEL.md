# Threat Model

STRIDE applied to an LLM inference platform, not a generic web service -
each threat below is the kind that's specific to running a model behind
a gateway, mapped to the control that actually exists in this
repository and the evidence that it works, not just that it was
intended to.

**Scope.** The gateway, vLLM, Redis, the Kubernetes cluster and its
policies, the CI/CD pipeline, and the planned Cloudflare Tunnel. Out of
scope: the Windows/WSL2 host OS, Docker Desktop itself, and GitHub's own
infrastructure - all trusted boundaries this project depends on but
does not control.

## Spoofing

| Threat | Control | Evidence |
| --- | --- | --- |
| A caller presents another tenant's identity | API keys are never stored in plaintext - only a SHA-256 hash is compared, and the raw key never outlives `auth.py`'s one function call | `app/auth.py`, ADR 0021 |
| A build pipeline that isn't this repository's own CI produces a signature Kyverno accepts | Keyless cosign signing ties the signature to an exact GitHub OIDC identity: this repository, this workflow file, `refs/heads/main` - not a key anyone could copy | ADR 0008, `deploy/policies/kyverno-verify-signatures.yaml` |
| GitHub's OIDC subject claim is matched against a stale/mutable format, letting a different repo's token pass | `use_immutable_subject` checked explicitly before any trust policy was written | ADR 0009, CLAUDE.md's OIDC note |

## Tampering

| Threat | Control | Evidence |
| --- | --- | --- |
| An image is modified after signing (registry compromise, MITM) | Cosign signature verification at admission, scoped per-namespace, enforced (`failureAction: Enforce`) | `docs/evidence/m3/03-unsigned-image-refused.txt`, `docs/evidence/m4/06-*` |
| Model weights are poisoned or substituted | `model-verify` Job checks a keyless-signed SHA-256 manifest against every downloaded file before vLLM ever starts, and fails closed | ADR 0012 |
| The live cluster is changed by hand, bypassing Git | Argo CD's `selfHeal` reverts any drift on the next reconcile | `docs/evidence/m3/05-argocd-self-heal.txt` |
| A request body is tampered with in transit | Not mitigated for the local Ingress (plain HTTP on localhost - a stated M3 limitation); the planned Cloudflare Tunnel terminates TLS at Cloudflare's edge, which covers the public path |  |

## Repudiation

| Threat | Control | Evidence |
| --- | --- | --- |
| No record of which tenant did what, or why a request was refused | One structured `chat_completion_settled` audit line per request, at every terminal outcome (success, every rejection reason, every error) - tenant, outcome, status, token counts, duration | `app/routes/chat.py::_audit`, `docs/evidence/m4/07-streaming-live.txt` |
| A cluster change has no record of who/why | Every change is a Git commit; ADRs record the decision at the time it was made, not reconstructed after | `docs/adr/` |
| **Gap**: audit lines are container stdout only - nothing ships them anywhere durable | Not mitigated. A real deployment would need a log pipeline (Loki, CloudWatch, anything); this one relies on `kubectl logs` still having the data, which rotates |  |

## Information Disclosure

| Threat | Control | Evidence |
| --- | --- | --- |
| Tenant A receives tenant B's cached answer | The response cache key includes the tenant's hash - no two tenants can ever share an entry | `app/cache.py`, `tests/test_cache.py::test_different_tenants_never_share_a_cache_entry` |
| A prompt containing PII (email, SSN, card number) is forwarded to the model or appears in a log | The prompt guard redacts these patterns before the request leaves the gateway; the audit log never contains prompt content at all, by construction | ADR 0022, `tests/test_privacy.py` |
| Secrets (API keys, tenant config, Grafana's admin password) committed in plaintext | SOPS + age - only encrypted values are ever committed; the private key never enters Git | ADR 0015 |
| Prometheus/Grafana internals exposed on the public tunnel | The tunnel (once live) exposes the gateway's `/v1/*` routes only - `/metrics`, Grafana, and Prometheus are never routed through it | `docs/evidence/m5/` (tunnel evidence) |
| A raw API key is recoverable from gateway memory or a core dump | Only the SHA-256 hash is ever held past the single `authenticate()` call - a dump of this process yields no usable credential | `app/auth.py` |

## Denial of Service

| Threat | Control | Evidence |
| --- | --- | --- |
| One tenant exhausts the model's capacity, starving every other tenant (**token exhaustion as DoS** - the plan names this explicitly) | Per-tenant token budgets, checked and reserved *before* the GPU is touched - confirmed live: tenant-b exhausted while tenant-a stayed at 100% success | `docs/evidence/m4/08-two-tenants-k6-run-post-rebuild.txt` |
| A tenant floods the gateway with requests | Sliding-window rate limit, atomic Lua reservation, race-tested | ADR 0021, `tests/test_tenancy.py` |
| Too many requests queue behind a saturated vLLM, so every request eventually times out instead of a clean, fast failure | Load shedding: a bounded in-flight ceiling returns `503` immediately once saturated, rather than queueing indefinitely | ADR 0024, `tests/load/saturation.js`, `.github/workflows/load-test.yml` |
| VRAM exhaustion crashes vLLM | Not prevented - `--kv-cache-memory-bytes` bounds normal operation, but a chaos-day test deliberately reproduces real exhaustion to record what actually happens | `docs/POSTMORTEM-001.md` |
| Redis becomes unavailable, silently disabling budget/rate-limit enforcement | `/readyz` checks Redis reachability and fails closed - the gateway leaves rotation rather than serving with no limits enforced | `app/routes/health.py` |

## Elevation of Privilege

| Threat | Control | Evidence |
| --- | --- | --- |
| A compromised container escapes to the node or escalates privilege | Kyverno pod-security baseline: non-root, numeric UID, `drop: [ALL]` capabilities, read-only root filesystem, no privilege escalation - enforced on every pod in `palisade`, by choice also on every pod this project itself builds in `monitoring` | ADR 0013, 0019 |
| An unsigned or tampered image is scheduled into the cluster | Signature verification at admission, now covering every first-party image including the gpu-exporter added in M4 | ADR 0018, `docs/evidence/m4/06-*` |
| A compromised pod uses the network to reach other services or the internet | Default-deny NetworkPolicy; vLLM has **zero** egress of any kind, confirmed with raw-IP/DNS/hostname probes and controls | ADR 0014, `docs/evidence/m3/04-networkpolicy-enforcement.txt` |
| A compromised CI job or leaked token gains standing cloud access | GitHub OIDC-federated, short-lived AWS credentials - no long-lived access key exists to leak | ADR 0009 |

## Supply chain (cross-cutting)

Every first-party image (gateway, model-verify, sops-cmp, gpu-exporter)
goes through the identical pipeline: build, Trivy HIGH/CRITICAL gate
(`exit-code: 1`, no silent downgrade), SBOM via Syft, keyless cosign
signature, SBOM attestation - all before the digest that reaches the
cluster is chosen. A tampered or re-pushed image without that exact
chain is refused at admission, not just at build time - the distinction
that makes this a supply-chain control rather than a CI nicety. vLLM's
own upstream image is the one named, accepted exception (trusted by tag,
not signature) - recorded honestly in M3's limitations rather than
quietly exempted from this table.

## Explicitly not modeled

- **Prompt injection is defence in depth, not solved.** The guard
  (ADR 0022) catches textbook phrasing; a determined attacker using
  synonyms, encoding, or multi-turn framing is not caught by anything
  here. Stated as a limitation at the point it was built, not
  discovered later.
- **Model poisoning via the training data itself.** Out of scope - this
  project serves a pre-trained model and verifies the weights it
  downloads match a known-good checksum; it has no opinion on how that
  checksum's own weights were produced.
- **Side-channel attacks on the GPU** (timing, power analysis) -
  genuinely out of scope for a portfolio project on shared consumer
  hardware.
