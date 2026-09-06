# 2. Getting a GPU into a pod on k3d under WSL2

- **Status:** Accepted
- **Milestone:** M0

## Context

Palisade serves a language model on a laptop RTX 3050 (4 GB VRAM). The cluster
is k3d - k3s running inside Docker containers - on Windows 11 via WSL2. The GPU
therefore has to cross four boundaries to reach a pod:

```
Windows driver -> WSL2 VM -> Docker container (k3d node) -> containerd -> pod
```

This was identified in planning as the single dependency that could force an
architecture change, so it was tackled before anything else was built, with a
fallback agreed in advance in case it could not be made to work.

## What actually happened

The first three boundaries were straightforward:

| Check | Result |
| --- | --- |
| `nvidia-smi` inside WSL2 Ubuntu | works |
| `docker run --gpus all ... nvidia-smi` | works |
| `docker exec <k3d-node> nvidia-smi` | works |
| `nvidia-container-cli info` inside the node | detects the RTX 3050 |

The last boundary is where it broke, and it broke twice for two unrelated
reasons.

### Failure 1 - the device plugin scheduled onto zero nodes

The NVIDIA device plugin Helm chart carries a default node affinity requiring
one of `feature.node.kubernetes.io/pci-10de.present`,
`feature.node.kubernetes.io/cpu-model.vendor_id=NVIDIA`, or
`nvidia.com/gpu.present`. Those labels are applied by NVIDIA's Node Feature
Discovery / GPU Feature Discovery, which was disabled (`gfd.enabled=false`) to
save memory on a 16 GB machine.

Helm reported the release as successful because the DaemonSet was created
correctly - it simply matched no nodes. `DESIRED = 0`, no pods, no error.

**A green `helm install` is not evidence that anything is running.**

Labelling the node by hand fixed the scheduling.

### Failure 2 - NVML is not supported under WSL2

With the DaemonSet finally scheduling, the pod crash-looped:

```
Failed to initialize NVML: Not Supported
error starting plugins: ... nvml init failed: Not Supported
```

The device plugin enumerates GPUs through NVML. Under WSL2 the GPU is not a
normal `/dev/nvidia*` device - it is `/dev/dxg`, a paravirtualised interface,
with the real driver living on the Windows side. NVML has no support for this.

**This is not fixable by configuration.** The device plugin cannot work here.

### The path that does work - CDI

`nvidia-ctk` detects WSL, locates the Windows driver store mounted into the VM,
and writes a Container Device Interface spec describing exactly which device
nodes and libraries to inject:

```
Auto-detected mode as 'wsl'
Selecting /dev/dxg as /dev/dxg
Using WSL driver store path: /usr/lib/wsl/drivers/nvlti.inf_amd64_...
```

### Failure 3 - a silent gap in the generated spec

The first CDI attempt still failed, with a subtly different error:

```
Failed to initialize NVML: N/A     # note: N/A, not "Not Supported"
```

The difference matters. `Not Supported` meant NVML could not work at all;
`N/A` meant `nvidia-smi` was present but could not reach the driver. Buried in
the generation log was the reason:

```
warning: Could not locate libdxcore.so: libdxcore.so: not found
```

`nvidia-ctk` looks for `libdxcore.so` inside the WSL driver store, but Docker
Desktop places it at `/usr/lib/x86_64-linux-gnu/libdxcore.so`. Generation warned
and continued, producing a spec that mounted `nvidia-smi` and `libnvidia-ml.so`
but not the library both depend on. Appending the missing mount to the spec made
it work.

## Decision

**On WSL2, inject the GPU with CDI. Do not deploy the NVIDIA device plugin.**

`scripts/setup-gpu-cdi.sh` runs after cluster creation and:

1. generates the CDI spec inside the live node container,
2. appends the missing `libdxcore.so` mount,
3. pins `nvidia-container-runtime` to `mode = "cdi"`.

It runs against a running node rather than at image build time because the
driver store path is host-specific and only knowable at runtime.

Pods then need two things:

```yaml
runtimeClassName: nvidia
metadata:
  annotations:
    cdi.k8s.io/gpu: "nvidia.com/gpu=all"
```

**On native Linux the device plugin is still used**, so `cluster-up.sh` branches
on whether it is running under WSL. The repository stays portable, and the
difference is explicit rather than accidental.

## Consequences

- **No scheduler-level GPU accounting on WSL2.** Nothing requests
  `nvidia.com/gpu`, so the scheduler does not know the GPU exists and will not
  stop two GPU pods landing on the same node. With one GPU and one vLLM replica
  this is acceptable, and it reinforces a decision made independently: Palisade
  does not autoscale the model tier, it does admission control and load shedding
  at the gateway instead (see ADR 0005).
- One extra image to keep in step with the k3s version; `make k3s-image`
  rebuilds it on a version bump.
- The acceptance test (`make gpu-check`) is a real scheduling test, not
  `docker run`. It proves the whole chain.
- A production deployment on real Linux GPU nodes would use the device plugin
  path, which this repo still supports. **Knowing why the two differ is the
  point of this ADR.**

## Fallback, if the above ever stops working

Run vLLM as a plain Docker container on the host with `--gpus all` and point an
in-cluster `Service` with manually defined `Endpoints` at it. This is a
legitimate **external model backend** pattern used in production when the
inference tier is managed separately. The gateway, policy, GitOps, supply-chain
and observability layers - the actual substance of this project - are unaffected
by which option is in use.

## Lessons worth repeating

1. A successful `helm install` says the objects were created, not that anything
   is running. Check `DESIRED`, not the exit code.
2. Read the whole log. The `libdxcore.so` warning was one line among forty and
   was the entire problem.
3. Error text is a fingerprint. `Not Supported` and `N/A` came from the same
   function and meant completely different things.
