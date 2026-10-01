# 0020 - GitOps bootstrap target, and policies before workloads

## Status

Accepted (live verification pending - see Consequences)

## Context

Two gaps showed up once M3 worked end to end on the long-lived cluster.

**Reproducibility.** Getting from `make up` to a running GitOps deployment took four
manual steps that existed nowhere except in shell history: provision the age key Secret
(`scripts/setup-sops-age.sh`), `terraform apply` in `infra/terraform/cluster` (Argo CD +
Kyverno), wait for Kyverno's webhooks, and `kubectl apply` the root Application. The plan
defines a milestone as finished only when its acceptance passes from a clean rebuild, and
a rebuild cannot reproduce steps that aren't written down.

**Ordering on a fresh cluster.** The root app-of-apps created `palisade-policies`,
`palisade-secrets` and `palisade` together, and each synced independently. On the
long-lived cluster this never mattered, because the policies had existed since before
any workload. On a fresh cluster, workload pods could be admitted *before* the Kyverno
ClusterPolicies and NetworkPolicies existed. Kyverno does not retroactively evict pods
it never saw, so they would keep running unchecked until their next restart. For a
milestone whose goal is "the cluster enforces the rules rather than trusting the
pipeline", a bootstrap race that skips enforcement is a real hole, not a cosmetic one.

## Decision

1. **`make gitops` (`scripts/gitops-up.sh`)** runs the non-GitOps steps in dependency
   order, and each step is idempotent:
   1. age key Secret, which comes first because Argo CD's repo-server mounts it;
   2. Terraform apply for Argo CD + Kyverno;
   3. wait for both to be Available, because Kyverno's webhooks must answer before
      anything syncs;
   4. pre-pull the vLLM image into the node with `ctr pull` (optional, `PREPULL=0`
      skips it; CLAUDE.md explains why `k3d image import` cannot be used);
   5. apply the root Application;
   6. wait until every Application is Synced + Healthy.
2. **Sync-waves on the child Applications**: `palisade-policies` -1, `palisade-secrets` 0,
   `palisade` 1.
3. **The `argoproj.io/Application` health check is restored** in `argocd-cm` (via
   `argocd-values.yaml`). Since Argo CD 1.8, a child Application counts as Healthy the
   moment it exists, so waves between Applications order *creation* but don't wait for
   the child to finish syncing. With the check restored, the root app holds wave 1 until
   the policies app actually reports Healthy. This is Argo CD's own documented pattern
   for app-of-apps ordering.
4. **`palisade-policies` gets `destination.namespace: palisade` and `CreateNamespace=true`.**
   Its NetworkPolicies live in that namespace, which the `palisade` chart used to create.
   With policies now syncing first, the namespace would not exist yet. The chart's own
   Namespace manifest adopts it afterwards, since `CreateNamespace` doesn't track what it
   creates.

## Alternatives considered

- **Install the policies with Terraform alongside Kyverno.** This guarantees ordering
  trivially. Rejected because policy changes would then go through `terraform apply`
  instead of git, and drift would no longer be self-healed. The policies are exactly
  what most needs to be under GitOps.
- **One Application for everything, ordered by sync-waves inside it.** Rejected: it couples
  the reviewed static policy set to the Helm chart's release cycle, and loses the
  separate health and sync status that make the policies' state legible on their own.
- **A Kyverno `failurePolicy`/background scan to catch pods admitted early.** Background
  scans *report* violations on existing pods; they don't stop them. Ordering prevents
  the window from existing at all, which is strictly better.

## Consequences

- The only out-of-band step left in the deployment is the age private key, which ADR
  0015 already accepts. Everything after it is reproducible from `make up && make gitops`.
- The Application health check is cluster-wide inside this Argo CD install. A child app
  that is degraded now also shows its parent as Progressing or Degraded. That is the
  intended signal, but it means `root` is no longer green while any child is not.
- **Verification status:** the change was written and linted while the cluster was
  down (the WSL VM restarted mid-task). The ordering has to be proven by the clean
  rebuild (`make down && make up && make gitops`), with policies observed Healthy
  before any palisade pod exists. That rebuild is the next M3 step.
