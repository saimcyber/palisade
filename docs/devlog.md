# Devlog

A running log of what I worked on, what broke, and what I learned building
Palisade. Newest entries at the top. The polished per-milestone write-ups live in
[`../documentation/`](../documentation/); this is the rougher day-to-day version.

---

## 2026-09-08 — M1 done: an OpenAI-compatible gateway in front of vLLM

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

## 2026-09-07 — reframed the plan around milestones

Rewrote the project plan so it's organised purely by milestone goal +
acceptance test, instead of by any kind of schedule. This is a side project
around a degree; I'd rather gate each milestone on "the test passes" than
pretend I know how long anything takes. Also fixed every shellcheck finding and
turned on the pre-commit hooks (gitleaks, detect-private-key, yaml/json checks).

## 2026-09-06 — M0: a GPU-capable k3d cluster on WSL2

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
