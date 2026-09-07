# 5. No autoscaling on the model tier

- **Status:** Accepted

## Context

Kubernetes' default answer to load is a `HorizontalPodAutoscaler` on CPU
utilization. The cluster has exactly one GPU (docs/adr/0002-gpu-in-k3d.md),
and the GPU is not visible to the scheduler as an allocatable resource here -
it arrives via CDI, which does not participate in Kubernetes' resource
accounting the way `nvidia.com/gpu` requests/limits normally would. A second
`vllm` replica would not get a second GPU; it would either fail to schedule
usefully or contend with the first replica for the same card, and a CPU-based
HPA would not even measure the thing that actually saturates first (VRAM),
so it would scale on a signal that has nothing to do with the real
bottleneck.

## Decision

`k8s/vllm.yaml` runs a single `Deployment` replica, deliberately, with no
`HorizontalPodAutoscaler`. `strategy: Recreate` is set instead of the default
`RollingUpdate`, because a rolling update would briefly want two pods
scheduled at once - both wanting the one GPU - which is exactly the
situation being avoided.

Load management on this tier is handled by two mechanisms that are honest
about the constraint instead of hiding it:

- **Admission control** - the gateway (M1 Task 4) rejects or queues requests
  once the model is saturated, rather than letting Kubernetes silently drop
  or queue them at a layer that has no visibility into GPU state.
- **Load shedding** - under sustained overload the gateway fails fast with a
  clear error rather than accepting work it cannot complete in reasonable
  time.

## Consequences

- Throughput on this milestone's hardware has a hard ceiling: one model,
  one GPU, one replica. This is a stated limitation, not a hidden one.
- If this ran on hardware with multiple real GPUs (cloud, or a workstation
  with the NVIDIA device plugin actually working), the honest path to more
  throughput is more replicas *with* proper `nvidia.com/gpu` resource
  requests so the scheduler can place them correctly - not a CPU-based HPA.
  That would need CDI's constraints from docs/adr/0002 revisited first.
- Because scaling is off the table, the interesting engineering problem
  becomes admission control and backpressure, not orchestration - which is
  where M1's gateway work actually goes.
