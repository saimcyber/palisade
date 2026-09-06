# 2. Running GPU workloads inside k3d

- **Status:** Accepted
- **Date:** 2026-09-06

## Context

Palisade serves a language model on a laptop RTX 3050 (4 GB VRAM). The cluster
is k3d - k3s running inside Docker containers. Getting a physical GPU through
two layers of containerisation is the single fiddliest part of the project, and
it is the one dependency that could force an architecture change, so it was
tackled on day one with a hard half-day time box.

Three things must all be true:

1. Docker must be able to pass the GPU to a container (`--gpus all`).
2. The k3s **node** container must itself contain the NVIDIA container runtime,
   otherwise containerd inside the node cannot hand the GPU to a pod - even
   though the node container can see it. The stock `rancher/k3s` image does not
   include it.
3. The NVIDIA device plugin must advertise `nvidia.com/gpu` as an allocatable
   resource so the scheduler will place a pod that requests one.

## Decision

Build a custom k3s node image (`docker/k3s-nvidia/Dockerfile`) that overlays the
k3s rootfs onto an `nvidia/cuda` base with `nvidia-container-toolkit` installed.
Create the cluster with `--gpus all`, then install the NVIDIA device plugin
pinned to `runtimeClassName: nvidia`.

k3s detects the runtime at startup and creates the `nvidia` RuntimeClass by
itself, so no containerd template override is needed.

### Fallback, if the above cannot be made to work

Run vLLM as a plain Docker container on the host with `--gpus all`, and point an
in-cluster `Service` with manually defined `Endpoints` at it. This is a
legitimate **external model backend** pattern used in production when the
inference tier is managed separately from the application tier. The gateway,
policy, GitOps, supply-chain and observability layers - which are the actual
substance of this project - are entirely unaffected by which option is in use.

## Consequences

- One extra image to build and keep in step with the k3s version. It is built
  once and cached, and `make k3s-image` rebuilds it on a version bump.
- The GPU is a single, non-replicable resource: exactly one vLLM pod can run.
  This is why Palisade does **not** autoscale the model tier, and instead does
  admission control and load shedding at the gateway. See `docs/adr/0005`.
- The acceptance test (`make gpu-check`) is a real scheduling test, not just
  `docker run`. It proves the whole path: Docker to node to containerd to
  device plugin to scheduler to pod.
