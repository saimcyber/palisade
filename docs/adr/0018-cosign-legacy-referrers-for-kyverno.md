# 0018 - cosign legacy signature layout, for Kyverno's sake

## Status

Accepted (third iteration - see both false starts below, kept rather than erased)

## Context

M3's acceptance criterion is a live one: push a Deployment referencing an
`ghcr.io/saimcyber/*` image, and Kyverno's `verify-palisade-image-signatures`
ClusterPolicy (ADR 0013) either admits it (signed) or refuses it with a readable reason
(unsigned). Deploying the palisade chart through the real app-of-apps sync, both the
gateway Deployment and the model-verify Job were refused - not because they weren't
signed, but because Kyverno reported `.attestors[0].entries[0].keyless: no signatures
found` against images this project had itself signed and pushed in M2/M3.

## False start #1: `--registry-referrers-mode=legacy`

Reproduced outside Kyverno first: `cosign verify` succeeded from the host and from a
cosign v3.1.3 pod inside the cluster, failed from a cosign v2.6.1 pod with the same
error Kyverno reported. `docker manifest inspect` showed GHCR held only a
no-`.sig`-suffix OCI-1.1-referrers fallback tag for the signed digest - no legacy
`sha256-<digest>.sig` tag at all. That evidence was real; the fix drawn from it wasn't.
`--registry-referrers-mode=legacy` looked like the right lever, broke CI twice finding
its actual scope (the installer's default predates it; `cosign attest` doesn't have it
at all in v3.1.3), and once both of those were fixed, a live redeploy with the
"corrected" images failed with the *exact same error* against the *exact same, newly
re-signed* digests. Checking the flag's own `--help` text properly at that point:
"mode for **fetching** references from the registry" - it governs what cosign reads
back, never what format `sign` writes. The whole premise was never true.

## False start #2: pin Kyverno below kyverno/kyverno#17363

Searched Kyverno's own issue tracker next and found kyverno/kyverno#17363, a confirmed
regression in v1.19.0/v1.19.1 where `verifyImages` fails against validly-signed images -
assigned to an unreleased v1.19.2 milestone. This looked like confirmation from an
independent source, so `kyverno_chart_version` was pinned down to `3.8.2` (app v1.18.2,
the newest pre-1.19 release) and applied live.

**It made no difference.** Kyverno v1.18.2 refused the identical images with the
identical error. This falsifies the hypothesis outright, on this project's own evidence,
not just a reread of the issue: #17363's own reporter notes in that thread that they have
no legacy `.sig` tag either, which in hindsight was the same signal false start #1 had
already produced - the two false starts were converging on the same underlying fact
(cosign v3's images genuinely have no legacy-tagged signature to find) from different
directions, and neither one noticed until the Kyverno-version variable was isolated and
shown not to matter. `kyverno_chart_version` was reverted to `3.9.1`.

## Real fix

Checked `--new-bundle-format` and `--use-signing-config` against both `cosign sign
--help` and `cosign attest --help` directly (both show as deprecated, not absent - a
different failure mode than false start #1's `--registry-referrers-mode`, which was
simply never valid on `attest`). Both parse on both commands. Set
`--new-bundle-format=false --use-signing-config=false` on every `cosign sign` and
`cosign attest` call in `.github/workflows/{ci,model-verify-image,sops-cmp-image}.yml`.
This is the actual write-path control: it forces the pre-bundle, pre-OCI-1.1
`sha256-<digest>.sig` / `.att` tag layout that Kyverno's verifier reads, rather than a
flag that only ever touched how cosign looks things up.

Before trusting this a third time, verified it against both of the checks the earlier
two attempts skipped: `docker manifest inspect` against the new digest's
`sha256-<digest>.sig` tag returns a real manifest (not "manifest unknown"), and a cosign
v2.6.1 pod inside the cluster - the same stand-in that first reproduced the failure -
verifies the new digest successfully. Only then was this pushed to a live resync.

## Alternatives considered

- **Pin `cosign-release` to a real v2.x release for the sign/attest step**, since v2
  writes the legacy layout natively with no flag needed. Not pursued: v3.1.3 is already
  the version verified against this project's own `cosign verify` calls everywhere else
  (ADR 0008); splitting signing onto an older major version than verification uses is a
  worse inconsistency than one pair of deprecated flags.
- **Try Kyverno's newer `type: SigstoreBundle` verifyImages mode**, on the chance it
  reads the new-format bundle directly and needs no flag change at all. Not pursued once
  the write-side flags were confirmed to work with the existing `ClusterPolicy` -
  migrating the verification mechanism was unnecessary once the simpler fix on the
  signing side was actually correct.

## Consequences

- `--new-bundle-format` and `--use-signing-config` are both marked deprecated by cosign
  itself; a future cosign major version may remove them, at which point this project
  will need either a real fix from Kyverno's side (a verifier that reads the new bundle
  format) or a different workaround - tracked here, not assumed to be permanent.
- The three already-pushed images (`palisade-gateway`, `palisade-model-verify`,
  `palisade-sops-cmp`) were rebuilt multiple times across this investigation (CI builds
  aren't reproducible, so each rebuild got a new digest); the `bump-digest` automation
  (ADR 0007) is what kept `values.yaml` and `argocd-values.yaml` pointed at whichever
  digest was actually live on GHCR at each step.
- Two live Argo CD resyncs and a Kyverno chart downgrade-then-revert happened against
  the running cluster while chasing this - all reversible, none left mid-state, but a
  real cost of testing hypotheses against a live system instead of a fully offline
  reproduction. The `docker manifest inspect` + in-cluster-verify gate above exists
  specifically so the next person debugging a signature-admission issue here checks
  the write format *before* the next live resync, not after.
