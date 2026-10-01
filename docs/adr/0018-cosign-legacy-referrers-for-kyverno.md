# 0018 - cosign legacy referrers mode, for Kyverno's sake

## Status

Accepted

## Context

M3's acceptance criterion is a live one: push a Deployment referencing an
`ghcr.io/saimcyber/*` image, and Kyverno's `verify-palisade-image-signatures`
ClusterPolicy (ADR 0013) either admits it (signed) or refuses it with a readable reason
(unsigned). Deploying `palisade-gateway` through the real app-of-apps sync, both the
gateway Deployment and the model-verify Job were refused - not because they weren't
signed, but because Kyverno reported `.attestors[0].entries[0].keyless: no signatures
found` against images this project had itself signed and pushed in M2/M3.

Reproduced outside Kyverno to separate "genuinely unsigned" from "policy can't find the
signature it's looking for":

- `cosign verify` (v3.1.3, the version pinned everywhere in this project) against the
  exact digest, from the WSL host: **succeeds**.
- The identical command, run as a throwaway pod inside the cluster using the
  `gcr.io/projectsigstore/cosign:v2.6.1` image: **fails**, `no signatures found`.
- The same command, same pod, `ghcr.io/sigstore/cosign/cosign:v3.1.3`: **succeeds**.
- `docker manifest inspect` against
  `ghcr.io/saimcyber/palisade-gateway:sha256-<digest>.sig` (the pre-OCI-1.1 tag
  convention): `manifest unknown`. Against
  `ghcr.io/saimcyber/palisade-gateway:sha256-<digest>` (no `.sig` suffix): a real
  `application/vnd.oci.image.index.v1+json` holding both the signature and the SBOM
  attestation.

cosign v3 signs using the Sigstore bundle format and, by default
(`--registry-referrers-mode=oci-1-1`), stores the result as an OCI 1.1 referrer. GHCR has
no Referrers API, so cosign falls back to a tag built from the digest with no `.sig`/
`.att` suffix. Kyverno v1.19.1's `verifyImages` Cosign attestor - checked directly
against its `go.mod` on the `release-1.19` branch, which does vendor
`sigstore/cosign/v3` - still only looks up the legacy `sha256-<digest>.sig` /
`sha256-<digest>.att` tags internally, not the OCI 1.1 referrer path. This is a known,
open upstream gap (kyverno/kyverno#17363: "verification fails ... for signatures stored
only as ... bundle referrers (worked on v1.18.1)"), not a misconfiguration on this
repository's policy or signing invocation.

## Decision

Pass `--registry-referrers-mode=legacy` to every `cosign sign` and `cosign attest` call
in `.github/workflows/{ci,model-verify-image,sops-cmp-image}.yml`. This makes cosign
additionally write the legacy `.sig`/`.att` tags Kyverno's current verifier can actually
find, alongside whatever OCI-1.1-aware tooling already reads. `cosign verify`
itself is unaffected either way - it checks both forms - so this changes nothing about
what a human or a CI step running cosign directly can confirm; it only changes what an
in-cluster admission controller stuck on the older convention is able to see.

## Alternatives considered

- **Downgrade Kyverno to v1.18.1**, the last version confirmed to read the legacy
  format correctly before this regression. Rejected: trading a current release for an
  older one to dodge a one-line signing flag is a worse trade, and the fix lives in the
  part of the chain this project actually controls (how it signs), not in a dependency it
  doesn't.
- **Wait for kyverno/kyverno#17363 to be fixed upstream.** Rejected as the only fix - it's
  open, with no committed timeline, and the acceptance criterion needs to be demonstrable
  now, on the Kyverno version actually running.
- **Switch the Kyverno policy to `ImageValidatingPolicy` (the newer CEL-based API)**,
  on the chance its verifier path handles OCI 1.1 referrers correctly. Not pursued: the
  GitHub issue's own title shows `ImageValidatingPolicy` hitting the *same* referrers gap
  on `v1.19.0`, so there was no reason to expect it would help here, and migrating the
  whole policy to a different API to work around a registry-fallback-format detail is a
  disproportionate fix for what is, from this repository's side, a one-flag problem.

## Consequences

- Every image this project signs going forward carries signatures/attestations in both
  layouts until Kyverno (or whatever eventually verifies these images) catches up to
  OCI 1.1 referrers - a deliberate, temporary duplication, not a permanent design choice.
- The three already-pushed images (`palisade-gateway`, `palisade-model-verify`,
  `palisade-sops-cmp`) needed to be re-signed under this flag before the live cluster
  could admit them; re-signing doesn't change an image's own digest, so no chart value
  or manifest needed to change - only the registry-side signature artifacts.
