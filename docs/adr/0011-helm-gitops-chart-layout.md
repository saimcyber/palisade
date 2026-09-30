# 11. Helm chart replaces raw manifests as the deployment path

- **Status:** Accepted

## Context

`k8s/vllm.yaml` (M1) is explicit, on purpose, that raw manifests were a
deliberate M1-only choice: "Helm and GitOps are M3's job... doing them here
would blur the milestones." M3's own goal is that git becomes the only
route to production - which means something has to own reconciling git
state to cluster state continuously, not just apply a file once by hand.

## Decision

A single Helm chart, `deploy/charts/palisade/`, templates both the gateway
and vLLM as one release - not two independent charts. They are one
application (a gateway with nothing behind it, or a model with nothing in
front of it, are both meaningless on their own), so one chart with two
Deployments reflects that more honestly than two charts Argo CD would have
to keep in sync separately.

Every hard-won M1 setting carries over unchanged, templated rather than
rewritten: `runtimeClassName: nvidia` + the `cdi.k8s.io/gpu` annotation
(docs/adr/0002), `enableServiceLinks: false` (the `VLLM_PORT` collision),
`strategy: Recreate` (docs/adr/0005, one GPU, one replica),
`--kv-cache-memory-bytes=512M` and `VLLM_WSL2_ENABLE_PIN_MEMORY=1`, and the
generous `startupProbe` budget for cold-cache model loads. None of that
was re-derived - it was proven once, expensively, in M1, and this chart's
only job is to keep applying it declaratively.

`k8s/vllm.yaml` and `k8s/*-check.yaml` are left in place, unmodified. They
are M0/M1's own acceptance-test manifests (`make gpu-check`,
`make cuda-check`) - re-run occasionally to confirm the raw GPU/CDI path
still works independent of anything Helm or Argo CD add on top. Deleting
them would remove a useful, narrower diagnostic for no benefit.

## Consequences

- Exactly one release to reason about, one values file, one place resource
  requests/limits and image references live - lower duplication risk than
  two charts that both need to agree on, for example, which Service name
  the gateway's `PALISADE_UPSTREAM_BASE_URL` points at.
- The gateway's image reference in `values.yaml` is pinned by digest, never
  a floating tag - both because that is simply correct practice, and
  because the Kyverno policy this milestone adds (docs/adr/0013) rejects
  `:latest` outright; a chart that shipped `:latest` would fail its own
  policy the moment Argo CD tried to sync it.
