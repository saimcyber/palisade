# 0019 - Numeric UID for every pod, and vLLM hardened rather than exempted

## Status

Accepted

## Context

Once Kyverno's signature check admitted the signed images (ADR 0018), the first real
sync produced two pods stuck in `CreateContainerConfigError`:

```
Error: container has runAsNonRoot and image has non-numeric user (palisade),
cannot verify user is non-root
```

Both first-party images end with `USER palisade` / `USER verify`, users created by
`useradd --system` (which happened to assign UID 999 in both). The pods set
`runAsNonRoot: true`, which `palisade-pod-security-baseline` (ADR 0013) requires.
The kubelet enforces that field by itself, *before* the container starts. A user
*name* gives it nothing to check without reading the image's `/etc/passwd`, so it
refuses. Kyverno had already admitted the pod, because the pod spec did say
`runAsNonRoot: true`. The admission policy and the kubelet check the same promise at
different layers, and only the kubelet needs a number.

The same sync exposed a second problem one wave later. ADR 0013 left open whether vLLM's
upstream image could satisfy the baseline at all. The vLLM Deployment had no
`securityContext` whatsoever: it ran as root, kept the default capability set and had a
writable root filesystem. It would have been denied the moment Argo CD reached sync-wave
1. Scratch-testing a hardened spec then surfaced two more issues that only appear under
these constraints:

- **Read-only root breaks cosign's TUF cache.** model-verify's `cosign verify-blob` writes
  Sigstore's trust root under `$HOME/.sigstore`. The image's `HOME` (`/home/verify`) was
  never created (`--no-create-home`), and the root filesystem is read-only, so cosign
  failed with `mkdir /home/verify: read-only file system`. The verifier failed closed and
  reported `REFUSED: manifest signature did not verify`, which was the correct outcome
  for the wrong reason.
- **The HF cache layout differs between the two pods.** model-verify calls
  `snapshot_download(cache_dir=$HF_HOME)`, which treats `/hf-cache` as the *hub* cache
  root (`/hf-cache/models--Qwen--Qwen3-0.6B`). vLLM with only `HF_HOME=/hf-cache` looks
  in `/hf-cache/hub/`. Downloading by commit SHA also writes no `refs/main`, so offline
  vLLM could not resolve a bare repo id either.

## Decision

1. **Every pod in the chart sets `runAsUser` / `runAsGroup` numerically**, from one chart
   value (`uid: 999`). The images are not rebuilt: the fix lives in the deployment
   contract, where the kubelet reads it, and the signed digests stay unchanged.
2. **vLLM is held to the same baseline as every other pod**: non-root (the same UID as
   model-verify, since the two share the HF cache PVC), `drop: [ALL]`,
   `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, seccomp `RuntimeDefault`.
   Everything it writes goes to emptyDirs (`/scratch` as `HOME` / `XDG_CACHE_HOME` /
   `VLLM_CACHE_ROOT` / `TRITON_CACHE_DIR`, plus `/tmp` and `/dev/shm`). `USER` /
   `LOGNAME` are set because UID 999 has no passwd entry in that image.
3. **vLLM runs explicitly offline**: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
   `VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1`, `HF_HUB_CACHE=/hf-cache`, and
   `--revision=<manifest commit>`. Zero egress is enforced by NetworkPolicy. These
   settings stop the process from *trying* to reach the network, so it doesn't stall
   on a call that can never succeed.
4. model-verify gets `HOME=/scratch` on an emptyDir for cosign's cache.
5. The model-verify Job gets `activeDeadlineSeconds: 900`. A pod that can never start is
   not a *failure* to the Job controller, so `backoffLimit` never fired, and Argo CD
   waited on the Sync hook indefinitely. That is what happened here. A deadline turns a
   silent hang into a visible failed sync.

## Alternatives considered

- **Change the Dockerfiles to `USER 999:999`.** This also works, and it makes the
  images self-describing. Not done *instead*: it means a rebuild, re-sign and three
  digest bumps for a fix the chart can express directly, and the pod spec should state
  its UID either way. Worth doing later as belt-and-braces.
- **A Kyverno `PolicyException` for vLLM.** This was the pre-agreed fallback if the
  upstream image could not run hardened. Not needed: it ran first time once the cache
  paths were redirected.
- **`fsGroup` instead of a shared UID.** `local-path` volumes are hostPath directories, and
  the kubelet does not apply `fsGroup` ownership changes to them. Matching UIDs is the
  mechanism that actually works on this storage class.

## Consequences

- No pod in the `palisade` namespace runs as root. That includes the third-party GPU
  workload, which is the one most often waved through.
- `uid: 999` is coupled to what `useradd --system` assigned when the images were built.
  If a future base image assigns a different system UID, the pod still runs, as 999,
  but files the image created for its own user would no longer be owned by the running
  process. Pinning the UID in the Dockerfiles would remove this coupling.
- vLLM's caches (compiled kernels, Triton) live in emptyDirs and are lost on restart. With
  `--enforce-eager` there is little to cache, so this costs nothing today.
