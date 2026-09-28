# 8. Image signing: cosign keyless, not key-based

- **Status:** Accepted

## Context

M2's goal is explicit: prove no long-lived cloud credential exists anywhere.
A signed image is only as trustworthy as whatever produced the signature -
if that's a private key, the key itself becomes exactly the kind of
long-lived secret the rest of this milestone is designed to eliminate.

## Decision

Sign with `cosign sign --yes`, keyless, through Sigstore - not
`cosign generate-key-pair` and a stored private key.

- **There is no private key to leak, store as a GitHub secret, back up, or
  rotate.** The workflow's own GitHub Actions OIDC token is the credential,
  valid for the duration of a single job run and nothing longer.
- **The signature's identity is verifiable and specific.** Fulcio issues a
  short-lived certificate binding the signature to the exact workflow file
  and ref that produced it
  (`https://github.com/saimcyber/palisade/.github/workflows/ci.yml@refs/heads/main`),
  which is what `cosign verify --certificate-identity` checks - a verifier
  isn't trusting "some key that claims to be Palisade's," they're trusting
  "this specific workflow, on this specific repo, on this specific branch."
- **Rekor gives a public, tamper-evident transparency log** of every
  signature, without either party having to run or trust a private log
  server.
- The alternative - generating a key pair, storing the private half as a
  `COSIGN_PRIVATE_KEY` GitHub secret - would work, but reintroduces the
  exact class of long-lived credential this milestone is built to prove
  doesn't need to exist.

## Consequences

- Verification requires network access to Fulcio/Rekor's public-good
  instances at verify time, not just at sign time - a fully air-gapped
  verification isn't possible with this approach. Acceptable here: nothing
  about this project runs air-gapped.
- Every signature is permanently, publicly logged in Rekor, including the
  workflow identity that produced it. That's the point, not a side effect -
  but it does mean signing is not something to do casually against
  unfinished or embarrassing builds, since the log entry is not something
  that can be quietly withdrawn later.
