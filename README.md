# Palisade

**A secure, self-hosted LLM inference platform.**
GitOps-delivered LLM serving with a verified supply chain, per-tenant token
budgets, and policy enforcement at admission.

> Status: **M1 — inference service running.** vLLM serves a model inside the
> local GPU cluster behind an OpenAI-compatible gateway, and the acceptance tests
> pass. Supply chain and GitOps come next (M2–M3).

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
```

`make help` lists everything.

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
| ~25 GB disk | Node image, CUDA base images, model weights |
| 16 GB RAM | The WSL2 VM is capped at 10 GB — see `.wslconfig` |

## Cluster profiles

The whole Linux VM is capped at 10 GB of RAM, so the stack is split:

| Target | Contents |
| --- | --- |
| `make up-lite` | Cluster + GPU support + the application |
| `make up-full` | Adds Argo CD and the observability stack |

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
