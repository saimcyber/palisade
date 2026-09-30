#!/usr/bin/env python3
"""Model-verification init container entrypoint.

Two checks, in order, either of which refusing to pass means this process
exits non-zero - which is the whole mechanism: Kubernetes runs
initContainers in sequence and only starts the main container once every
init container has exited 0.

  1. The manifest's own signature verifies (cosign verify-blob, keyless,
     against this project's own GitHub Actions identity). Nothing in the
     manifest is trusted before this passes - an attacker who could modify
     the manifest file alone still couldn't produce a valid signature for
     the modified content.
  2. Every file the (now-trusted) manifest lists, once downloaded via the
     same huggingface_hub mechanism vLLM itself uses, hashes to exactly the
     SHA-256 the manifest says it should.

Environment:
  MODEL_MANIFEST          manifest basename under /app/manifests/ (default: qwen3-0.6b)
  HF_HOME                 shared cache dir - must match what vLLM's own container reads
  CERT_IDENTITY            cosign --certificate-identity (default: this repo's ci.yml on main)
  CERT_OIDC_ISSUER          cosign --certificate-oidc-issuer (default: GitHub Actions)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MANIFEST_DIR = Path("/app/manifests")
DEFAULT_IDENTITY = "https://github.com/saimcyber/palisade/.github/workflows/model-manifest.yml@refs/heads/main"
DEFAULT_ISSUER = "https://token.actions.githubusercontent.com"


def die(msg: str) -> None:
    print(f"REFUSED: {msg}", file=sys.stderr)
    sys.exit(1)


def verify_manifest_signature(manifest_path: Path, bundle_path: Path) -> None:
    identity = os.environ.get("CERT_IDENTITY", DEFAULT_IDENTITY)
    issuer = os.environ.get("CERT_OIDC_ISSUER", DEFAULT_ISSUER)
    if not bundle_path.exists():
        die(
            f"no signature bundle at {bundle_path} - refusing to trust an unsigned manifest"
        )
    result = subprocess.run(
        [
            "cosign",
            "verify-blob",
            "--bundle",
            str(bundle_path),
            "--certificate-identity",
            identity,
            "--certificate-oidc-issuer",
            issuer,
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        die(f"manifest signature did not verify:\n{result.stderr}")
    print(f"signature OK: {manifest_path.name} matches {identity}")


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    name = os.environ.get("MODEL_MANIFEST", "qwen3-0.6b")
    manifest_path = MANIFEST_DIR / f"{name}.json"
    bundle_path = MANIFEST_DIR / f"{name}.sigstore.json"
    if not manifest_path.exists():
        die(f"no manifest baked into this image at {manifest_path}")

    verify_manifest_signature(manifest_path, bundle_path)

    manifest = json.loads(manifest_path.read_text())
    repo, revision, files = manifest["repo"], manifest["revision"], manifest["files"]
    print(f"trusted manifest: {repo}@{revision[:12]} ({len(files)} files)")

    # Same download mechanism vLLM's own engine uses internally, so the
    # cache this writes is exactly what vLLM will find already present -
    # no separate cache format to keep in sync by hand.
    from huggingface_hub import snapshot_download

    cache_dir = os.environ.get("HF_HOME")
    snapshot_dir = Path(
        snapshot_download(repo_id=repo, revision=revision, cache_dir=cache_dir)
    )
    print(f"snapshot ready at {snapshot_dir}")

    mismatches = []
    for filename, info in sorted(files.items()):
        fpath = snapshot_dir / filename
        if not fpath.exists():
            mismatches.append(f"{filename}: MISSING")
            continue
        actual = sha256_of_file(fpath)
        expected = info["sha256"]
        if actual != expected:
            mismatches.append(
                f"{filename}: expected {expected[:16]}... got {actual[:16]}..."
            )
        else:
            print(f"  ok  {filename}  {actual[:16]}...")

    if mismatches:
        die(
            "hash mismatch on "
            + str(len(mismatches))
            + " file(s):\n"
            + "\n".join(mismatches)
        )

    print(f"PASS: all {len(files)} files verified against a signed manifest")


if __name__ == "__main__":
    main()
