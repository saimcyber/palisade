# 16. Argo CD via Terraform, app-of-apps via git

- **Status:** Accepted

## Context

M3's goal names two different things that both have to be true: git is the
*only* route to production (nothing gets applied by a person running
`kubectl apply` against the live cluster), and the cluster *itself*
enforces the rules rather than trusting whatever pipeline produced a
manifest. Something has to continuously reconcile git state to cluster
state, and that something is infrastructure in its own right - it has to
come from somewhere too.

## Decision

**Argo CD and Kyverno are installed via Terraform's Helm provider**
(`infra/terraform/cluster/`), applied by hand against the local k3d
cluster - never by CI, which has no route to this laptop's cluster and no
reason to. This is genuinely different infrastructure from
`infra/terraform/aws/*`: no OIDC identity, no CI-applied root, because
nothing outside this machine can reach a k3d cluster running on it. One
Terraform apply stands up both the GitOps engine and the policy engine
that will go on to enforce everything else.

**Everything after that is app-of-apps.** A single `Application`
(`deploy/argocd/root-app.yaml`) is the one resource still applied by hand
- `kubectl apply -f` it once, immediately after Argo CD exists. It points
at `deploy/argocd/apps/`, and Argo CD syncs every `Application` it finds
there: the `palisade` chart, the `palisade-policies` directory (Kyverno
`ClusterPolicy` + `NetworkPolicy`, plain manifests, no templating needed),
and `palisade-secrets` (the SOPS-encrypted `Secret`, decrypted via the CMP
sidecar - ADR 0015). Adding, changing or removing an `Application` file
under `deploy/argocd/apps/` is now the entire mechanism for changing what
runs in the cluster - which is the literal, checkable meaning of "a push
to git deploys itself."

**Every `Application` sets `syncPolicy.automated: {prune: true,
selfHeal: true}`.** `selfHeal` is what makes "the cluster enforces the
rules" more than a one-time admission check: a manual `kubectl edit` on a
synced resource - drift, or someone bypassing the intended path entirely -
gets reverted back to what git says, not silently tolerated until the next
scheduled sync.

## Consequences

- The one true bootstrap sequence for a from-scratch cluster is now: `make
  up` (the GPU-capable k3d cluster, unchanged from M0/M1) ->
  `terraform apply` in `infra/terraform/cluster/` (Argo CD + Kyverno
  exist) -> `scripts/setup-sops-age.sh` (the one secret Argo CD itself
  needs to read other secrets) -> `kubectl apply -f
  deploy/argocd/root-app.yaml` (everything else, forever after, is git).
  Four manual steps, once, to reach a state where zero manual steps remain
  for every change after.
- `selfHeal: true` means a live demonstration of "the cluster enforces the
  rules" doesn't require breaking anything by editing git - manually
  patching a running resource to drift from what's committed and watching
  Argo CD revert it is itself evidence worth recording alongside the
  signature-refusal demonstration.
