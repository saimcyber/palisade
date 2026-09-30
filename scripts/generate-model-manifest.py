#!/usr/bin/env python3
"""Generate a signed-integrity manifest for a Hugging Face model repo.

Run by hand whenever the pinned model changes (rare - the served model is a
deliberate, reviewed choice, not something that updates itself). The
manifest this writes is what M3's model-verification init container checks
downloaded weights against, and what ci.yml's model-manifest job signs.

For LFS-tracked files (the actual weights - large, content-addressed by
git-lfs) Hugging Face's own repo API reports a real SHA-256 (the LFS "oid"),
used directly. For small, non-LFS files (README, config, tokenizer vocab)
the Hub API only exposes a git blob SHA-1, not SHA-256 - so those are
downloaded once here and hashed independently instead. Either way, every
hash in the resulting manifest is a real SHA-256 of real file content, not
guessed or copied from memory.

Usage:
    python3 scripts/generate-model-manifest.py Qwen/Qwen3-0.6B \
        deploy/model-manifests/qwen3-0.6b.json
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request


def sha256_of_url(url: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url) as resp:
        while chunk := resp.read(1 << 20):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} <org/repo> <output.json>")
    repo, out_path = sys.argv[1], sys.argv[2]

    with urllib.request.urlopen(
        f"https://huggingface.co/api/models/{repo}?blobs=true"
    ) as resp:
        meta = json.load(resp)

    revision = meta["sha"]
    files: dict[str, dict] = {}
    for sib in meta["siblings"]:
        name = sib["rfilename"]
        lfs = sib.get("lfs")
        if lfs and len(lfs.get("sha256", "")) == 64:
            files[name] = {
                "sha256": lfs["sha256"],
                "size": lfs["size"],
                "source": "hf-lfs-oid",
            }
        else:
            url = f"https://huggingface.co/{repo}/resolve/main/{name}"
            digest, size = sha256_of_url(url)
            files[name] = {"sha256": digest, "size": size, "source": "computed"}
        print(f"  {name}: {files[name]['sha256'][:16]}... ({files[name]['source']})")

    manifest = {"repo": repo, "revision": revision, "files": files}
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {out_path} ({len(files)} files)")


if __name__ == "__main__":
    main()
