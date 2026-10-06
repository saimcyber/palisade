# Palisade

**A secure, self-hosted LLM inference platform.**
GitOps-delivered LLM serving with a verified supply chain, per-tenant token
budgets, and policy enforcement at admission.

> Status: **M4 — multi-tenant, metered, and watched.** Per-tenant token
> budgets and rate limits (Redis-backed, atomic reservation) sit in front of
> every request, alongside a response cache and a prompt guard. Two tenants
> sending real traffic diverge exactly as designed — one exhausted its budget
> and got `429`s while the other stayed unaffected —
> [recorded run](docs/evidence/m4/01-two-tenants-k6-run.txt). Prometheus,
> Grafana (four dashboards) and five alert rules run as their own
> Argo-CD-managed stack, deliberately unable to block the gateway or vLLM if
> something in it breaks. Everything from M3 — Argo CD deploys from git,
> Kyverno refuses unsigned images, no egress from vLLM — still holds. Next:
> M5, resilience and proof.

---

## Why I'm building this

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
services/        the gateway and the model runtime
infra/terraform/ AWS (S3, IAM, OIDC) and cluster add-ons
deploy/          Helm chart, Argo CD apps, Kyverno policies, SOPS secrets
observability/   Grafana dashboards and Prometheus alert rules
docker/          the GPU-capable k3s node image
scripts/         lifecycle and verification scripts
k8s/             standalone manifests (currently the GPU acceptance test)
docs/            architecture, ADRs, threat model, SLO, runbook
documentation/   a Word document per milestone — what was built and why
tests/           unit, integration and k6 load tests
```

## Documentation

- [`docs/devlog.md`](docs/devlog.md) — running notes, newest first
- [`docs/adr/`](docs/adr/) — architecture decision records
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — how I work on this and what I've settled on
- [`documentation/`](documentation/) — the polished per-milestone write-ups

## License

MIT — see [LICENSE](LICENSE).
