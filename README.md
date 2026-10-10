# Palisade

**A secure, self-hosted LLM inference platform.**
GitOps-delivered LLM serving with a verified supply chain, per-tenant token
budgets, and policy enforcement at admission.

> Status: **M5 in progress — resilience and proof.** Chaos day, the load
> test, and all five engineering documents below are done; a clean-rebuild
> acceptance pass and the milestone's own Word doc are not yet — see the
> [status table](#status) for exactly what's left. A signed image built from
> the wrong GitHub Actions workflow is refused by Kyverno exactly like an
> unsigned one, even though the signature itself is real —
> [recorded run](docs/evidence/m5/05-chaos-wrong-identity-signature.txt). Two
> real bugs were found by deliberately breaking the system — not by review,
> not by a test, by a `kubectl delete pod` and a `redis-cli CLIENT PAUSE` —
> and fixed, tested, and re-verified live:
> [postmortem](docs/POSTMORTEM-001.md). Load shedding caps how many requests
> reach vLLM at once, refunding the reservation on every shed. Every claim
> about what this platform can and can't do is now written down in one place
> each: [`THREAT-MODEL.md`](docs/THREAT-MODEL.md),
> [`SLO.md`](docs/SLO.md), [`RUNBOOK.md`](docs/RUNBOOK.md),
> [`COST.md`](docs/COST.md), [`ARCHITECTURE.md`](docs/ARCHITECTURE.md).
> Everything from M3/M4 — Argo CD deploys from git, per-tenant budgets and
> rate limits, Prometheus/Grafana watching without being able to block
> anything — still holds, verified from a clean rebuild.

### This is what happens when you try to deploy an unsigned image

```
$ kubectl apply -f unsigned-pod.yaml
Error from server: error when creating "/tmp/unsigned-pod.yaml": admission webhook "mutate.kyverno.svc-fail" denied the request:

resource Pod/palisade/gateway-unsigned was blocked due to the following policies

verify-palisade-image-signatures:
  verify-gateway-signature: 'failed to verify image ghcr.io/saimcyber/palisade-gateway@sha256:c07cca10...: .attestors[0].entries[0].keyless: sigstore bundle verification failed: no matching signatures found'
```

Not a demo flag, not a staged failure — this is the cluster's real
admission webhook, on the actual pod spec the gateway Deployment uses,
differing from a working one only in the image digest
([full transcript](docs/evidence/m3/03-unsigned-image-refused.txt)). The
same policy refuses a **validly signed** image too, if it was signed by
the wrong GitHub Actions workflow
([recorded run](docs/evidence/m5/05-chaos-wrong-identity-signature.txt)) —
a real signature isn't enough; it has to be *this repo's* signature.

---

## Status

| Milestone | State |
| --- | --- |
| M0 Foundations | Complete — verified from a clean rebuild |
| M1 Inference service | Complete — gateway streams real tokens from the GPU, in-cluster |
| M2 Supply chain & CI/CD | Complete — signed, SBOM-attested image on ghcr.io; OIDC-only AWS access |
| M3 Kubernetes, GitOps & policy | Complete — push deploys itself; unsigned image refused; verified from a clean rebuild |
| M4 Platform & observability | Complete — per-tenant budgets/rate limits enforced live; Prometheus+Grafana+alerts running, verified from a clean rebuild |
| M5 Resilience & proof | **In progress.** Done: k6 saturation test in CI, chaos day (5 experiments, 2 real bugs found/fixed/verified live), load shedding, all five docs (`ARCHITECTURE`/`THREAT-MODEL`/`SLO`/`RUNBOOK`/`COST`), the blameless postmortem. Not yet done: a clean-rebuild acceptance pass, the Cloudflare Tunnel demo, the M5 engineering Word doc, and a fresh-clone verification. The demo video called for in the plan is deliberately deferred. |



This is a personal learning project. I'm a Cyber Security undergrad going into
platform / DevOps engineering, and I wanted one project where I actually build
the infrastructure an AI company runs *around* a model — not just deploy a
container. So Palisade is an open-source LLM on a local GPU wrapped in
authentication, per-customer spending limits, abuse filtering, caching,
monitoring, and a delivery pipeline that refuses to ship anything it can't
cryptographically verify.

I work through it as milestones **M0–M5**, each gated on an acceptance test. The
[devlog](docs/devlog.md) has the day-to-day notes; [`documentation/`](documentation/)
has the polished per-milestone write-ups — including the dead ends, because
those are where the learning is.

## Quickstart

```bash
make tools      # install the pinned toolchain (idempotent)
make doctor     # verify the environment, including GPU passthrough
make up         # create the local k3d cluster with GPU support
make gpu-check  # acceptance: a scheduled pod must see the GPU
make gitops     # age key, Argo CD + Kyverno, root app; waits until all Synced
```

After `make gitops`, the only way to change what runs is to push to `main`.
`make help` lists everything.

> **Reproducing this from a fork:** the gateway's Secret is encrypted to *my*
> age key, which is never committed. On a fresh machine `make gitops` generates
> a new key; add its public key to `.sops.yaml` and re-encrypt
> `deploy/secrets/gateway-secret.enc.yaml` (with your own API-key hash) before
> `palisade-secrets` can sync. Point the Argo CD Applications at your fork, and
> re-sign images from your own CI identity, or Kyverno will — correctly — refuse
> them.

## GPU access

On **WSL2** the NVIDIA device plugin cannot be used: it discovers GPUs through
NVML, which is unsupported against WSL's `/dev/dxg` driver model. Palisade
injects the GPU with **CDI** instead, so a pod needs both:

```yaml
runtimeClassName: nvidia
metadata:
  annotations:
    cdi.k8s.io/gpu: "nvidia.com/gpu=all"
```

On **native Linux** the device plugin is used as normal, giving real
scheduler-level GPU accounting. `scripts/cluster-up.sh` branches on the host.
The full investigation — three separate failures, including a one-line warning
that was the entire problem — is in
[`docs/adr/0002-gpu-in-k3d.md`](docs/adr/0002-gpu-in-k3d.md).

## Requirements

| Requirement | Notes |
| --- | --- |
| Linux or WSL2 | Developed on WSL2 / Ubuntu 24.04 |
| Docker | With GPU passthrough (`docker run --gpus all`) |
| NVIDIA GPU | Developed against an RTX 3050 Laptop, 4 GB VRAM |
| ~50 GB disk | The vLLM image alone unpacks to ~26 GB inside the node; plus node/CUDA images and weights |
| 16 GB RAM | The WSL2 VM is capped at 10 GB — see `.wslconfig` |

## Cluster profiles

The whole Linux VM is capped at 10 GB of RAM, so the stack is split:

| Target | Contents |
| --- | --- |
| `make up-lite` | Cluster + GPU support (the application arrives via `make gitops`) |
| `make up-full` | Reserved for M4's observability stack — today identical to `up-lite` |

Turning off what you are not currently working on is a deliberate operational
choice on constrained hardware, not a shortcut.

## Repository layout

```
services/              the gateway and the model runtime
infra/terraform/       AWS (S3, IAM, OIDC) and cluster add-ons
deploy/                Helm chart, Argo CD apps, Kyverno policies, SOPS secrets
deploy/observability/  Grafana dashboards and Prometheus alert rules
docker/                the GPU-capable k3s node image, the project-built gpu-exporter
scripts/               lifecycle and verification scripts
k8s/                   standalone manifests (currently the GPU acceptance test)
docs/                  architecture, ADRs, threat model, SLO, runbook, cost, postmortems
docs/evidence/         raw transcripts proving each milestone's claims, M3 through M5
documentation/         a Word document per milestone — what was built and why
tests/                 unit, integration and k6 load tests
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system diagrams, sync-wave ordering, trust boundaries
- [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md) — STRIDE mapped to real controls, and what's explicitly out of scope
- [`docs/SLO.md`](docs/SLO.md) — the SLIs/targets this platform is actually measured against
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — one entry per alert that actually exists, no speculative entries
- [`docs/COST.md`](docs/COST.md) — real cloud GPU pricing vs. real hosted-API pricing, worked out honestly
- [`docs/POSTMORTEM-001.md`](docs/POSTMORTEM-001.md) — two real bugs chaos testing found, blameless write-up
- [`docs/evidence/`](docs/evidence/) — raw command transcripts proving every claim above actually happened
- [`docs/adr/`](docs/adr/) — architecture decision records, including the dead ends and what was rejected
- [`docs/devlog.md`](docs/devlog.md) — running notes, newest first
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — how I work on this and what I've settled on
- [`documentation/`](documentation/) — the polished, dual-register (plain-language + technical) per-milestone write-ups

## License

MIT — see [LICENSE](LICENSE).
