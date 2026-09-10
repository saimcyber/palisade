# Conventions

Conventions for working in this repository.

## Environment

Developed inside **WSL2 Ubuntu 24.04**, repo at `~/palisade` on the Linux filesystem —
not on `/mnt/*`. The Windows mount is slow for many small files and does not honour Unix
permission bits, which matters for the `age` keys and cosign material used from M2.

Hardware target: NVIDIA RTX 3050 Laptop (4 GB VRAM), 16 GB RAM, WSL2 capped at 10 GB.
That cap covers the *whole* WSL VM — Ubuntu, the docker-desktop distro and k3d together —
which is why the stack is split into `make up-lite` and `make up-full`.

## Entry points

```bash
make doctor      # 28 environment checks; exits non-zero, so CI can gate on it
make tools       # install/upgrade the pinned toolchain (idempotent)
make up          # create the cluster with GPU support
make gpu-check   # acceptance test: a scheduled pod must drive the GPU
make down        # tear down
```

`make help` lists everything.

## Standing rule: a document per milestone

At the end of each milestone, write `documentation/_build/m<N>.py` and build the Word document:

```bash
cd documentation/_build && python build.py m<N>
```

It must cover: everything done; what differed from the plan and why; how it was done;
the limitations of the result; and why each tool was chosen over its alternatives — each
explained **both in plain language and technically** (use the `dual()` helper). See
`documentation/README.md` for the full structure and `M0-Foundations.docx` for the quality bar.

## No time references, anywhere

**This project is tracked by goal, not by schedule.** It may take a week or a year;
that is not a property worth recording. Therefore:

- **No calendar dates.** Not in documents, ADRs, commit bodies, READMEs or the LICENSE.
- **No day or week allocations.** Milestones are M0-M5 and are done when their
  acceptance test passes - not "Day 1" or "Days 2-4".
- **No elapsed-time claims.** Not "this took an afternoon", "~4 min build", "a half-day
  time box". Where the point was that work was *bounded*, say it was bounded by a
  pre-agreed fallback, which is the part that actually mattered.
- **No "Completed on" fields.**

**What is exempt** - these are runtime behaviour, not scheduling, and must stay:
`--timeout=180s`, `sleep 4`, `timeout 90`, `ttlSecondsAfterFinished: 300`, retry
budgets, and any latency SLO in M4/M5 (p95 latency is a measurement, not a deadline).

Check for regressions with:

```bash
make check-time
```

It uses `git grep`, so it only inspects tracked files and never wanders into
`.venv` or `.git`.

## Conventions

- **Verify a version exists before pinning it.** Query the upstream release API and
  confirm the download URL returns 200. A previously-pinned Trivy version did not exist.
- **Pin everything.** `latest` is not reproducible. `scripts/install-tools.sh` compares
  installed vs pinned and reinstalls only on mismatch.
- **Fixes belong in scripts, not in your shell history.** If something had to be done once
  by hand, put it in `scripts/` so `make up` reproduces it.
- **Test from a clean teardown**, not incrementally. That is how the `nvidia` RuntimeClass
  race was found.
- **Write the ADR when the decision is made**, in `docs/adr/`. Record exclusions too —
  knowing what not to build is part of the design.
- **Check `DESIRED`, not the exit code.** A green `helm install` means objects were
  created, not that anything is running.

## GPU

The NVIDIA device plugin **cannot work under WSL2** — it enumerates through NVML, which is
unsupported against `/dev/dxg`. The GPU is injected with **CDI** instead. Pods need both:

```yaml
runtimeClassName: nvidia
metadata:
  annotations:
    cdi.k8s.io/gpu: "nvidia.com/gpu=all"
```

`nvidia-ctk` omits `libdxcore.so` from the generated spec; `scripts/setup-gpu-cdi.sh`
appends it. Without it NVML fails with `N/A` rather than `Not Supported` — different
error, different cause. `scripts/cluster-up.sh` branches: CDI on WSL2, device plugin on
native Linux. Full write-up in `docs/adr/0002-gpu-in-k3d.md`.

vLLM under WSL2 needs `VLLM_WSL2_ENABLE_PIN_MEMORY=1` — its platform layer disables
pinned memory on any WSL2 kernel by default, and vLLM v0.28's engine hard-requires it
for UVA-backed buffers; without the var, startup fails with `RuntimeError: UVA is not
available`. Safe here since our kernel is well past the 4.19.121 floor vLLM checks for.
On a 4 GB card, `--gpu-memory-utilization 0.85` is too high (WSL2/the desktop already
holds back part of the card). `0.7` was enough on host Docker, but running the same
image in-cluster through a k3d node reproducibly hit `torch.OutOfMemoryError` at
KV-cache allocation at 0.7 *and* 0.6 *and* with `--max-model-len` halved to 2048 - each
attempt died needing only 30-50 MiB more, which halving context length barely moved.
That means vLLM's percentage-based KV-cache auto-sizing is working from a skewed number
somewhere in the nested k3d-node-container CDI path, not that the budget was merely too
small. Fix: `--kv-cache-memory-bytes=512M`, which bypasses the percentage calculation
and states the KV cache size directly.

A Kubernetes `Service` named the same as an app whose own env vars share its prefix is a
real bug, not cosmetic: k8s injects `<SERVICE>_PORT` etc. for every Service a pod can
see, so a Service named `vllm` overwrote `VLLM_PORT` (which vLLM reads for its own
internal IPC) with a URI, crashing with `ValueError: VLLM_PORT '...' appears to be a
URI`. The "Unknown vLLM environment variable" warnings for `VLLM_SERVICE_HOST` etc. seen
earlier were the same collision - mostly harmless noise, except for this one. Fix:
`enableServiceLinks: false` on the pod spec, which stops the injection entirely.

## Layout

```
services/        gateway (FastAPI) and model runtime (vLLM)
infra/terraform/ AWS (S3, IAM, OIDC) and cluster add-ons
deploy/          Helm chart, Argo CD apps, Kyverno policies, SOPS secrets
observability/   Grafana dashboards, Prometheus alert rules
docker/          GPU-capable k3s node image
scripts/         lifecycle and verification
k8s/             standalone manifests
docs/adr/        architecture decision records
documentation/   per-milestone build documentation
tests/           unit, integration, k6 load
```
