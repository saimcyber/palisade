# 0017 - PersistentVolumeClaim health override for WaitForFirstConsumer

## Status

Accepted

## Context

`vllm-hf-cache` is annotated `argocd.argoproj.io/sync-wave: "-1"` so it exists before
the model-verify Job (wave 0, the first pod to mount it) and the vLLM Deployment
(wave 1, the second). Argo CD will not create a wave's resources until every resource
in the previous wave reports health status `Healthy` - that is the entire point of
sync-waves.

On a real sync, this deadlocked. The `local-path` StorageClass (k3d's default, and the
only one available here) sets `volumeBindingMode: WaitForFirstConsumer`: a PVC using it
stays in phase `Pending` - by design - until some pod that references it is scheduled,
at which point the provisioner creates the underlying hostPath on that pod's node and
binds it. Argo CD's built-in health check for `PersistentVolumeClaim` reports `Pending`
as not-`Healthy`. So: the PVC cannot become `Healthy` until a consumer pod exists, and
no consumer pod can be created until the PVC's wave is `Healthy`. Confirmed live -
`vllm-hf-cache` sat in `Pending` indefinitely, `palisade-policies` and `palisade-secrets`
synced fine in parallel, and the `palisade` Application itself stayed `OutOfSync
Progressing` with no Job and no pods in the namespace.

## Decision

Override Argo CD's health assessment for `PersistentVolumeClaim` via
`resource.customizations.health.PersistentVolumeClaim` in `argocd-cm` (set through the
Terraform Helm release's `configs.cm`, in `infra/terraform/cluster/argocd-values.yaml`):
a PVC with any `status.phase` set (`Pending` or `Bound`) is reported `Healthy`; only a
PVC with no status at all is `Progressing`. Sync-wave ordering still determines apply
*order* (the PVC manifest reaches the API server before the Job's), which is all the
ordering guarantee this chart actually needs - the storage class's own
`WaitForFirstConsumer` semantics, not Argo CD, are what make the Job's pod bind the
volume correctly on first mount.

## Alternatives considered

- **A dedicated StorageClass with `volumeBindingMode: Immediate`.** Would make the PVC
  bind (and go `Healthy`) before any consumer exists, sidestepping the health check
  entirely. Rejected: `local-path-provisioner` only knows which node to create the
  hostPath directory on by looking at where the first consumer pod was scheduled: binding
  immediately, before that pod exists, defeats the one thing the provisioner needs
  `WaitForFirstConsumer` for. It would work by accident on this single-node k3d cluster
  and fail the moment this ran on anything with more than one node - not a trade I want
  recorded as the real fix.
- **Drop the sync-wave annotation and let the PVC apply in the same wave as its
  consumers.** Does not remove the deadlock: Argo CD still waits for the previous wave's
  resources (now including the PVC) to be `Healthy` before moving to the next wave if
  there is more than one wave at all, and the model-verify Job and vLLM Deployment
  genuinely do need to stay in separate waves (ADR 0012) regardless of what wave the PVC
  sits in.
- **Mark the PVC a Sync hook instead of sync-wave-only.** Hooks have the same
  health-gating behavior for wave ordering; this would not have changed the outcome.

## Consequences

- This override is scoped to the `PersistentVolumeClaim` kind cluster-wide, inside this
  one Argo CD installation - it affects how Argo CD *reports* PVC health in its UI/API,
  not how Kubernetes binds the volume. A genuinely stuck PVC (no provisioner, quota
  exceeded, no matching node) still shows `status.phase: Pending` and would now read
  `Healthy` in Argo CD even though it is not usable - a real loss of signal, accepted
  because the alternative is the sync deadlocking this project is built to demonstrate
  does *not* happen. `kubectl get pvc` remains the authoritative check for actual binding
  state; Argo CD's health badge is not it for this one resource kind.
