# Devlog

A running log of what I worked on, what broke, and what I learned building
Palisade. Newest entries at the top. The polished per-milestone write-ups live in
[`../documentation/`](../documentation/); this is the rougher day-to-day version.

---

## M3 done: the cluster enforces the rules itself

Argo CD now deploys everything from git (app-of-apps: policies, then secrets,
then workloads), and Kyverno refuses any of my images that my own CI didn't sign.
The recorded refusal is in `docs/evidence/m3/`.

What broke, roughly in order:

- Kyverno rejected images `cosign verify` was happy with. Four wrong fixes
  before I decoded the stored certificate and found an empty intermediate chain.
  The real fix was `type: SigstoreBundle` in the policy (ADR 0018).
- Pods were admitted and then never started: `runAsNonRoot` can't be checked
  against a user *name*. Numeric `runAsUser` in the chart (ADR 0019).
- vLLM had no security context at all. Hardened rather than exempted:
  non-root, read-only, offline, zero egress.
- A sync-wave deadlock (gateway readiness waits on vLLM, vLLM's wave waited on
  the gateway), a hook Job that could hang forever, and two fields the API
  server silently dropped. Argo CD said "Synced" through some of these, so
  `kubectl diff` became my main check.
- `make gitops` makes the bootstrap reproducible. A clean rebuild passes, with
  every policy created before the first workload pod (ADR 0020).

## M2 done: the pipeline signs what it ships

GitHub Actions builds, scans (Trivy gate), pushes and keylessly signs the
gateway with an SBOM attestation. AWS access is OIDC-only, with separate plan
and apply roles. The big gotcha: GitHub's OIDC subject claim uses the new
immutable `owner@id/repo@id` format for newer repos, and the old format fails
with a bare `AccessDenied`. Details in `documentation/M2-Supply-Chain-CICD.docx`.

## M1 done: an OpenAI-compatible gateway in front of vLLM

Got vLLM serving Qwen3-0.6B *inside* the k3d cluster (not just in host Docker),
put a small FastAPI gateway in front of it, and made `make gpu-check` +
the M1 acceptance test pass.

Three bugs cost me most of the time, and all three were worth learning:

- **`--gpu-memory-utilization` on a 4 GB card.** `0.7` worked in host Docker but
  OOM'd at KV-cache allocation once the same image ran through a k3d node — at
  0.7, 0.6, and even with the context length halved. Each attempt died needing
  only 30–50 MiB more, which is the tell that the percentage is being computed
  from a wrong total somewhere in the nested-container CDI path. Fix: state the
  KV cache size directly with `--kv-cache-memory-bytes=512M`.
- **Naming a Service `vllm`.** Kubernetes injects `<SERVICE>_PORT` env vars for
  every Service a pod can see, so it overwrote `VLLM_PORT` (which vLLM uses for
  its own internal IPC) with a URI and crashed. Fix: `enableServiceLinks: false`.
- **`VLLM_WSL2_ENABLE_PIN_MEMORY=1`** — vLLM disables pinned memory on any WSL2
  kernel by default, but its engine now hard-requires it. Without the var,
  startup fails with `RuntimeError: UVA is not available`.

Notes are in `docs/CONVENTIONS.md`; the full write-up is
`documentation/M1-Inference-Service.docx`.

## reframed the plan around milestones

Rewrote the project plan so it's organised purely by milestone goal +
acceptance test, instead of by any kind of schedule. This is a side project
around a degree; I'd rather gate each milestone on "the test passes" than
pretend I know how long anything takes. Also fixed every shellcheck finding and
turned on the pre-commit hooks (gitleaks, detect-private-key, yaml/json checks).

## M0: a GPU-capable k3d cluster on WSL2

First real milestone. The hard part was GPU access: the NVIDIA device plugin
can't work under WSL2 because it goes through NVML, which isn't supported
against `/dev/dxg`. Ended up injecting the GPU with **CDI** instead — a pod
needs `runtimeClassName: nvidia` *and* the `cdi.k8s.io/gpu` annotation, and
`nvidia-ctk` leaves `libdxcore.so` out of the generated spec so a script has to
append it. Full story in `docs/adr/0002-gpu-in-k3d.md`.

Set up the repo skeleton, a `make doctor` that runs ~28 environment checks, and
a pinned toolchain installer. Learned the hard way to verify a version actually
exists before pinning it — I pinned a Trivy release that had never shipped and
got a 404 mid-install.
