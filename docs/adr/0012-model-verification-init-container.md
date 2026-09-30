# 12. Model weights are verified by a signed manifest, not trusted on download

- **Status:** Accepted

## Context

vLLM downloads Qwen3-0.6B's weights from the Hugging Face Hub itself, the
first time it starts. Nothing currently checks that what actually lands on
disk is what was intended to be served - a corrupted download, a
person-in-the-middle on that connection, or (worse) a revision bump nobody
reviewed would all serve, silently, as if nothing had changed.

Hugging Face doesn't cryptographically sign individual files. What it does
provide, authoritatively, through its own repo API, is a real SHA-256 for
every LFS-tracked (large) file - the git-lfs content-addressing "oid" - and
a git blob hash for everything else. That's a real integrity anchor, but on
its own it only proves "this is the file HF is currently serving," not "a
human reviewed and accepted this specific file."

## Decision

**Two independent checks, both required, run by an initContainer before
vLLM's own container ever starts:**

1. **A manifest of expected file hashes is generated once, by hand**
   (`scripts/generate-model-manifest.py`), reading real hashes from Hugging
   Face's own API for LFS files, and independently downloading and hashing
   the handful of small non-LFS files itself (HF only exposes a git SHA-1
   for those, not a SHA-256). The output,
   `deploy/model-manifests/qwen3-0.6b.json`, is committed to the repo.
2. **That manifest is signed** by a dedicated workflow
   (`model-manifest.yml`), keylessly, with the same cosign/Sigstore
   identity every other signed artefact in this project uses (ADR 0008).
   The signature bundle is committed back to the repo alongside the
   manifest.
3. **The init container verifies the signature first, the hashes second.**
   `cosign verify-blob` against the manifest has to pass before a single
   byte of its contents is trusted; only then does the container download
   the model (via `huggingface_hub.snapshot_download` - literally the same
   call vLLM's own engine makes internally, so the cache it produces is
   exactly what vLLM expects to find already there) and hash every file
   against the now-trusted manifest. Any mismatch, or a missing signature
   bundle, exits non-zero - which is sufficient on its own to stop the pod,
   since Kubernetes runs `initContainers` in order and never starts the
   main container until every one of them has exited 0.

## Consequences

- This is honestly a **project-asserted** chain of trust, not an
  **upstream-asserted** one - it proves the weights match what *this
  project* reviewed and signed off on at manifest-generation time, not that
  Hugging Face's own distribution was never compromised. Stated plainly as
  a limitation (§9 of the M3 document), not implied to be stronger than it
  is.
- Updating the served model is now a deliberate, two-step, auditable act:
  regenerate the manifest, commit it, let CI sign it - not something that
  can happen silently by vLLM simply resolving a moved `main` ref
  differently on a different day. The manifest pins an exact revision
  commit, not a branch name.
- The verifier's own trusted data (the manifest + its signature bundle)
  ships baked into the init container's image, immutably, rather than
  being fetched at runtime from a location that could itself be tampered
  with independently of the image's own supply chain (ADR 0007, 0008).
