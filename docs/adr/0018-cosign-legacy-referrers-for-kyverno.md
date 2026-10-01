# 0018 - pin Kyverno below its v1.19.0/v1.19.1 verifyImages regression

## Status

Accepted (supersedes this ADR's own first version - see "False start" below; kept
under the same number and file because the investigation that got here is the
substance worth keeping, not just the conclusion)

## Context

M3's acceptance criterion is a live one: push a Deployment referencing an
`ghcr.io/saimcyber/*` image, and Kyverno's `verify-palisade-image-signatures`
ClusterPolicy (ADR 0013) either admits it (signed) or refuses it with a readable reason
(unsigned). Deploying the palisade chart through the real app-of-apps sync, both the
gateway Deployment and the model-verify Job were refused - not because they weren't
signed, but because Kyverno reported `.attestors[0].entries[0].keyless: no signatures
found` against images this project had itself signed and pushed in M2/M3.

## False start: cosign v3 / OCI 1.1 referrers

Reproduced outside Kyverno first, to separate "genuinely unsigned" from "policy can't
find the signature it's looking for": `cosign verify` (v3.1.3) against the exact digest
succeeded from the WSL host; the identical check inside a throwaway pod in the cluster
also succeeded with cosign v3.1.3 but failed with v2.6.1 ("no signatures found"). That,
plus `docker manifest inspect` showing GHCR holds only a no-`.sig`-suffix
`application/vnd.oci.image.index.v1+json` fallback tag for the signed digest, looked
exactly like the known cosign-v3-writes-OCI-1.1-referrers-only story: GHCR has no
Referrers API, cosign v3 falls back to a tag Kyverno's older lookup convention
allegedly can't read.

The fix this pointed to - `cosign sign --registry-referrers-mode=legacy` - broke CI
twice in a row before being abandoned:

1. The pinned `cosign-installer` default resolved to v3.0.6, which doesn't have the flag
   at all (`unknown flag`). Pinned the installer to v3.1.3 explicitly to fix that.
2. With v3.1.3, `cosign sign` accepted the flag and completed, but `cosign attest`
   doesn't have this flag in v3.1.3 at all - caught by a second real CI failure, not
   checked up front. Dropped the flag from the `attest` calls.
3. Re-deployed with the "fixed" images. Kyverno refused them with the exact same
   error, against the exact same (new, freshly re-signed) digests. Checked
   `--registry-referrers-mode`'s own `--help` text properly this time: it is
   "mode for **fetching** references from the registry" - it governs what cosign
   reads back during its own operations, not what format it writes a new signature in.
   The flag never did what the hypothesis needed it to do, on either command.

This is recorded rather than deleted because it is exactly the kind of deviation this
project's documentation standard exists to keep: a plausible-looking fix, pinned to a
confirmable mechanism (GHCR's lack of a Referrers API is real), that turned out to be
chasing the wrong layer of the stack - and the two CI failures it caused along the way
are part of that, not noise to clean up.

## Real root cause

Read Kyverno's own open issue tracker instead of continuing to guess: kyverno/kyverno#17363 is
a confirmed regression, present in both v1.19.0 and v1.19.1 (the version this project
had installed), where `verifyImages` fails against signatures that are valid and that
Kyverno's own vendored cosign library can parse correctly - the bug is in Kyverno's own
trust-material/bundle-detection handling introduced in v1.19.0, not in how or where the
signature is stored. The issue's own reporter confirms there is no legacy `.sig` tag to
fall back to in their case either - ruling out the referrers-format theory on Kyverno's
own evidence, not just this project's. It's assigned to the v1.19.2 milestone; as of this
pin, v1.19.2 has not been released (latest tag on the `kyverno/kyverno` GitHub repo is
still v1.19.1).

## Decision

Pin `kyverno_chart_version` (`infra/terraform/cluster/variables.tf`) to `3.8.2` - app
version v1.18.2, the newest release in the 1.18.x line, one minor version behind the
chart repo's current latest (3.9.1 / v1.19.1) - and stay there until v1.19.2 ships and
is itself verified against the live chart index before bumping. 3.8.2 was chosen over
3.8.1 only because the index briefly lists two different digests under 3.8.1 (one
resolving to an app-version string of `v1.18.1-rc.2`, the other to the real `v1.18.1`) -
3.8.2 has no such ambiguity and is strictly newer.

Reverted every `--registry-referrers-mode` flag and the comments that justified them;
kept the `cosign-release: "v3.1.3"` pin on `cosign-installer` across all four
workflows, since pinning to one explicitly verified cosign version instead of trusting
the installer's own default is a good practice independent of the flag that originally
motivated it.

## Alternatives considered

- **Wait for kyverno/kyverno#17363 to be fixed upstream and stay on v1.19.1 in the
  meantime.** Rejected as the only path: it's open with no shipped fix, and the
  acceptance criterion needs to be demonstrable now, on a Kyverno version that actually
  works.
- **Switch the Kyverno policy to the newer CEL-based `ImageValidatingPolicy` API**, on
  the chance its verifier path doesn't hit this bug. Not pursued: it's a disproportionate
  migration for what turned out to be a one-line chart-version pin, and nothing in the
  issue suggests the newer API is unaffected (it's a lower-level bundle-detection bug).

## Consequences

- This project runs one minor version behind Kyverno's current release, deliberately,
  with the exact upstream issue and the condition for moving forward (v1.19.2 shipping)
  recorded here rather than left as an unexplained stale pin for someone to rediscover.
- The three already-pushed images (`palisade-gateway`, `palisade-model-verify`,
  `palisade-sops-cmp`) were rebuilt twice during this investigation (CI builds aren't
  reproducible, so each rebuild got a new digest); the `bump-digest` automation
  (ADR 0007) is what kept `values.yaml` and `argocd-values.yaml` pointed at whichever
  digest was actually live on GHCR at each step, exactly as designed.
