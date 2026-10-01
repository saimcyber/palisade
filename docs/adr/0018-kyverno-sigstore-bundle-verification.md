# 0018 - Kyverno verifyImages: use type: SigstoreBundle, not Cosign

## Status

Accepted (fifth and final attempt in this investigation - the four before it are kept
below, not erased, because each one's evidence was real even when its conclusion
wasn't, and the next person hitting a similar error should see the whole path)

## Context

M3's acceptance criterion is a live one: push a Deployment referencing an
`ghcr.io/saimcyber/*` image, and Kyverno's `verify-palisade-image-signatures`
ClusterPolicy (ADR 0013) either admits it (signed) or refuses it with a readable reason
(unsigned). Deploying the palisade chart through the real app-of-apps sync, both the
gateway Deployment and the model-verify Job were refused - not because they weren't
signed, but because Kyverno reported `.attestors[0].entries[0].keyless: no signatures
found` against images this project had itself signed and pushed in M2/M3.

The policy's `verifyImages` rules didn't set `type:` at all, which defaults to `Cosign` -
Kyverno's legacy verifier, built around cosign's pre-bundle, pre-OCI-1.1 signature
layout. That default, not anything wrong with the signatures, turned out to be the
entire problem.

## Four false starts

**1. `--registry-referrers-mode=legacy`.** cosign v3 signs in the modern Sigstore bundle
format; GHCR has no OCI 1.1 Referrers API, so cosign falls back to a tag with no `.sig`
suffix that the `Cosign` verifier can't find - `docker manifest inspect` confirmed no
legacy tag existed. This flag looked like the fix. It wasn't: its own `--help` text says
it governs what cosign *fetches*, never what `sign` writes. Broke CI twice finding its
actual scope (the installer's pinned default predates it; `cosign attest` doesn't have
it at all in v3.1.3) before a live redeploy with "fixed" images failed with the identical
error, disproving it outright.

**2. Pin Kyverno below kyverno/kyverno#17363.** That issue describes a confirmed
v1.19.0/v1.19.1 regression in `verifyImages`, which looked like independent
confirmation. Downgraded to chart 3.8.2 (app v1.18.2) and tested live: identical
failure, identical images. Falsified on this project's own evidence - the issue's own
reporter also had no legacy tag, the same fact false-start #1 had already surfaced from
a different angle.

**3. `--new-bundle-format=false --use-signing-config=false`.** The actual write-path
flags, confirmed against both `cosign sign --help` and `cosign attest --help` directly
this time. Kyverno found the resulting legacy-tagged signature - real progress - then
failed one layer down: `x509: certificate signed by unknown authority`. A cosign v2.6.1
pod inside the same cluster chained the identical certificate without issue, ruling out
a network or CA-availability problem.

**4. Isolate the two flags; enable `features.tuf.enabled`.** cosign's CLI enforces that
`--new-bundle-format=false` cannot be set without `--use-signing-config` also being
explicit - `--use-signing-config=true` doesn't satisfy it either, so the pairing was not
optional, and a commit that dropped it broke signing outright in CI (reverted
immediately). Separately, discovered Kyverno's chart ships `features.tuf.enabled: false`
by default, meaning it checks certificates against a root baked into the binary at build
time rather than the live Sigstore TUF root - a real, independently worth-fixing
discovery. Enabled it (`infra/terraform/cluster/kyverno-values.yaml`) and re-tested live.
**No change** - identical x509 error, with TUF enabled, on both chart versions. This
ruled out both the Kyverno-version hypothesis (#2) and a stale-trust-root hypothesis as
the root cause, though TUF stayed enabled on its own merits (see Decision).

## Decisive test

Decoded the actual certificate the legacy-format signature carried
(`openssl x509 -in cert.pem -noout -issuer -ext authorityKeyIdentifier`, pulled from the
`dev.sigstore.cosign/certificate` manifest annotation). The leaf certificate itself was
fine - issued by production Fulcio (`O=sigstore.dev, CN=sigstore-intermediate`), correct
GitHub Actions identity embedded, 10-minute validity as expected. But the sibling
`dev.sigstore.cosign/chain` annotation - meant to carry the intermediate CA certificate
needed to build a trust path from that leaf back to a root - was **zero bytes**. Nothing
in the chain Kyverno has to work with connects the leaf to anything it trusts, TUF or
not. `cosign sign --use-signing-config=false` is not writing a usable chain into the
legacy-format OCI layer; cosign's own CLI verifies fine regardless because it always
supplements from its live TUF cache rather than relying solely on that annotation.

Confirmed this was fixable two ways, with hand-applied scratch `ClusterPolicy` objects in
a throwaway `sigtest` namespace (never touched by Argo CD, so self-heal couldn't
interfere), against the already-pushed, already-tested image digests - no new CI run, no
new digest, no PR:

- **T1**: the existing `Cosign`-type policy, with the real Fulcio intermediate + root PEM
  (fetched from `https://fulcio.sigstore.dev/api/v1/rootCert`, confirmed its Subject Key
  Identifier matches the leaf's Authority Key Identifier) pinned directly into
  `attestors[].entries[].keyless.roots`. **Admitted** - confirmed in the admission
  controller's own logs: `image attestors verification succeeded`.
- **T2**: `type: SigstoreBundle` instead, against a *different* image digest that had
  never been signed with the broken legacy-format flags at all - plain cosign v3
  defaults, modern bundle format, no flags, no pinned roots. **Also admitted** - same
  confirmed log line.

## Decision

Use **T2**: set `type: SigstoreBundle` on both `verifyImages` rules in
`deploy/policies/kyverno-verify-signatures.yaml`, and revert every `cosign sign`/
`cosign attest` call in `.github/workflows/{ci,model-verify-image,sops-cmp-image}.yml`
back to plain defaults - no `--new-bundle-format`, no `--use-signing-config`, no legacy
flags of any kind. `SigstoreBundle` reads cosign's actual, unmodified output; nothing
about it depends on a cosign behavior (the empty-chain write) that only shows up under a
specific, now-abandoned flag combination.

`features.tuf.enabled: true` stays. It never independently fixed this bug, but a
dynamically fetched, current Sigstore trust root is a real improvement over one frozen
at Kyverno's build time, and the live tests above ran *with* it enabled throughout - it
isn't implicated in anything that went wrong, and there's no reason to revert a
correctness improvement found along the way.

## Alternatives considered

- **T1's approach (pin Fulcio's roots directly into the policy).** Rejected in favor of
  T2 even though it also passed: it carries an operational liability T2 doesn't - Fulcio
  rotates its intermediate CA periodically, and a pinned PEM would need to be refreshed
  by hand before the next rotation or admission would start failing again, silently,
  for a completely different reason than anything in this ADR. `SigstoreBundle` has no
  such expiry.
- **Pin `cosign-release` to a real v2.x release for signing**, since v2 writes the
  legacy layout's chain correctly and natively, with no flag needed. Not pursued once
  T2 confirmed the policy-side fix works with plain v3 signing - no reason to split
  signing onto an older major version than this project verifies everything else with.

## Consequences

- The Kyverno policy now depends on `type: SigstoreBundle` being available, which
  required Kyverno ≥ roughly v1.19 (confirmed present via
  `kubectl explain clusterpolicy.spec.rules.verifyImages.type`) - a floor this project
  is already above.
- Every image this project signs now needs zero special signing flags - plain
  `cosign sign`/`cosign attest`, matching the version verified everywhere else (ADR 0008).
- Four live Argo CD resyncs, two Kyverno chart version changes (applied then reverted),
  and a TUF feature toggle happened against the running cluster while chasing this.
  All were reversible and none left the cluster mid-state, but it is the real cost of
  testing hypotheses against a live system - the scratch-namespace technique that
  finally isolated the cause (T1/T2) cost nothing against the live `palisade` app and
  should be the first resort next time, not the last.
