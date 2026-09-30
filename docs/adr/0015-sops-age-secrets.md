# 15. Secrets are SOPS+age encrypted in git, decrypted by a CMP sidecar

- **Status:** Accepted

## Context

`PALISADE_API_KEY_HASHES` is the gateway's one real secret. M3's goal is
that git is the only route to production - which a plaintext value in an
env var, applied by hand outside of Argo CD's sync, would quietly violate
for exactly the one value that matters most.

## Decision

**SOPS, with age as the encryption backend, not GPG.** Age has no keyring
to manage, no web of trust, and a keypair that's two short strings - a
much smaller thing to operate correctly than GPG for a single-operator
project.

**The encrypted `Secret` manifest is committed to git as ordinary-looking
YAML** (`deploy/secrets/gateway-secret.enc.yaml`) - every field name and
structure is visible; only the values are `ENC[AES256_GCM,...]` blocks.
`.sops.yaml` at the repo root pins which files (`deploy/secrets/*.enc.yaml`)
encrypt against which age public key. The matching private key is **never
committed** - generated once, kept at `~/.config/palisade/age.key`, and
provisioned into the cluster by a dedicated, idempotent script
(`scripts/setup-sops-age.sh`) that creates a `sops-age` Kubernetes Secret
in the `argocd` namespace - the same "secrets to create secrets need one
non-GitOps bootstrap step, run by hand, once" pattern M2's AWS bootstrap
identity already established (ADR 0009).

**Decryption happens inside Argo CD itself**, via a sidecar Config
Management Plugin (CMP) on `repo-server` running `sops -d`, mounting the
`sops-age` Secret. This is what makes it genuine GitOps for secrets, not
just encrypted-at-rest storage: a push that changes
`gateway-secret.enc.yaml` gets picked up and applied the same way a push
that changes the Helm chart does - no separate, manual "remember to run
this script" step for every secret change, only for the one-time key
provisioning.

## Consequences

- If `~/.config/palisade/age.key` is lost with no backup, every secret
  encrypted against it becomes permanently unrecoverable - re-encrypt
  against a newly generated key is the only path forward, and every
  existing `.enc.yaml` file would need updating. Stated plainly: this
  project keeps no backup of that key beyond the one machine that
  generated it, which is an acceptable risk for a single-operator
  portfolio project and would not be for a team one.
- The CMP sidecar's exact wiring (`repoServer.extraContainers`,
  `configs.cmp.plugins`) was written against the current, documented
  Argo CD Helm chart pattern but not yet exercised against a live sync -
  the M3 document records whether it worked as designed on first deploy
  or needed a fix, not a description of intended behaviour presented as
  a verified result.
- The demo API key hashed into `gateway-secret.enc.yaml` is exactly that -
  a demo value generated for this project, never a production credential -
  stated here and in the file's own committed comment, not left to be
  assumed.
