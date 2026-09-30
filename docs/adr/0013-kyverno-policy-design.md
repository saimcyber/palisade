# 13. Kyverno enforces at admission, scoped to what this project controls

- **Status:** Accepted

## Context

M2 makes it hard to *ship* an unsigned or vulnerable artefact. Nothing yet
stops someone - or some future version of this project's own CI, misconfigured
- from *running* one anyway. M3's own goal is explicit: the cluster enforces
the rules, not just the pipeline. That means an admission controller, and a
real decision about how broadly its rules apply.

## Decision

**Kyverno's `ClusterPolicy` API (`kyverno.io/v1`), not the newer CEL-based
policy types Kyverno is migrating toward.** `ClusterPolicy` is the
long-established, thoroughly documented surface with abundant real
examples to verify field-by-field syntax against; the CEL-based
`ValidatingPolicy`/`ImageValidatingPolicy` types are actively stabilizing
as of the pinned Kyverno version. Chosen deliberately over the newer path,
not out of not knowing about it - a documented, defensible trade-off, not
an oversight.

**Four policies, each scoped as narrowly as the thing it's actually
claiming to enforce:**

1. `verify-palisade-image-signatures` - the money-shot policy. Keyless
   cosign verification (`verifyImages`, `attestors.entries[].keyless`)
   against this exact repository's GitHub Actions identity, scoped to
   `ghcr.io/saimcyber/*` images only. vLLM's own upstream image is
   deliberately **not** required to carry this project's signature - it
   never could, and a blanket cluster-wide signature requirement would
   just force an exemption for it anyway. Scoping the policy to what this
   project actually signs is the honest version of that exemption, not a
   workaround for one.
2. `disallow-latest-tag` - cluster-wide, not namespace-scoped. A floating
   tag undermines the entire point of a digest-pinned supply chain (ADR
   0007, 0008) everywhere, not just in one namespace.
3. `palisade-pod-security-baseline` - non-root, all capabilities dropped,
   read-only root filesystem, explicit resource limits. Scoped to the
   `palisade` namespace only - `kube-system`, Traefik and Argo CD's own
   components are outside what this project controls or is making a claim
   about, and a cluster-wide version of this policy would just need
   exemptions carved out for all of them.

Every field the gateway's own Deployment sets (`securityContext.runAsNonRoot`,
`capabilities.drop: [ALL]`, `readOnlyRootFilesystem`, `resources.limits`)
was written to already satisfy this baseline, not loosened after something
got rejected.

## Consequences

- A signature-verification failure produces a specific, readable admission
  error naming the image and the policy - the strongest single
  demonstration this project can make, and the M3 document records the
  actual denial message from a real attempt, not a description of what one
  would look like.
- Whether vLLM's own upstream image can actually satisfy
  `palisade-pod-security-baseline` unmodified (particularly non-root and a
  read-only root filesystem, for an image built by a third party for GPU
  inference) is an open question this ADR does not answer in advance - the
  M3 document records what an actual deploy attempt found, and either
  confirms it works or documents the specific, narrow exemption that was
  needed and why.
