# Working notes

How I work on Palisade, and the conventions I've settled on as I go. This is a
personal learning project — I'm building it to get hands-on with platform
engineering, Kubernetes and LLM infrastructure, so these notes are as much for
future-me as anyone else.

## My setup

I develop this inside **WSL2 Ubuntu 24.04**, with the repo at `~/palisade` on the
Linux filesystem — not under `/mnt/*`. The Windows mount is slow for many small
files and doesn't honour Unix permission bits, which matters for the `age` keys
and cosign material from M2 onwards.

Hardware: NVIDIA RTX 3050 Laptop (4 GB VRAM), 16 GB RAM, WSL2 capped at 10 GB.
That cap covers the *whole* WSL VM — Ubuntu, the docker-desktop distro and k3d
together — which is why the stack is split into `make up-lite` and `make up-full`.

## Entry points

```bash
make doctor      # 28 environment checks; exits non-zero, so CI can gate on it
make tools       # install/upgrade the pinned toolchain (idempotent)
make up          # create the cluster with GPU support
make gpu-check   # acceptance test: a scheduled pod must drive the GPU
make down        # tear down
```

`make help` lists everything.

## How I track progress

The project is organised as milestones **M0–M5**, each with an acceptance test
that has to pass before I call it done. I keep a running [devlog](devlog.md) with
dated entries — what I did, what broke, what I learned — and at the end of each
milestone I write that up properly (see [`documentation/`](../documentation/)).

## Things I've settled on

- **Verify a version exists before pinning it.** I query the upstream release API
  and check the download URL returns 200 first — I once pinned a Trivy version
  that had never been released and hit a 404 mid-install.
- **Pin everything.** `latest` isn't reproducible. `scripts/install-tools.sh`
  compares installed vs pinned and reinstalls only on a mismatch.
- **One-off fixes go into a script, not just my shell history.** If I had to do
  something by hand once, it belongs in `scripts/` so `make up` reproduces it.
- **Test from a clean teardown**, not incrementally — that's how I found the
  `nvidia` RuntimeClass race.
- **Write the ADR when I make the decision**, in `docs/adr/`. I record what I
  decided *not* to build too.
- **Check `DESIRED`, not the exit code.** A green `helm install` means objects
  were created, not that anything is actually running.

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
available`. Safe here since my kernel is well past the 4.19.121 floor vLLM checks for.
On a 4 GB card, `--gpu-memory-utilization 0.85` is too high (WSL2/the desktop already
holds back part of the card). `0.7` was enough on host Docker, but running the same
image in-cluster through a k3d node reproducibly hit `torch.OutOfMemoryError` at
KV-cache allocation at 0.7 *and* 0.6 *and* with `--max-model-len` halved to 2048 - each
attempt died needing only 30-50 MiB more, which halving context length barely moved.
That means vLLM's percentage-based KV-cache auto-sizing is working from a skewed number
somewhere in the nested k3d node-container CDI path, not that the budget was merely too
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
