# -*- coding: utf-8 -*-
"""Content for the M1 engineering document."""
from docx_kit import *  # noqa: F403
from m0 import dual, _steps, _qa  # reuse the shared rendering helpers

SECTIONS = [
    "cover", "what_it_was_for", "starting_point", "decisions",
    "what_was_built", "how_it_was_done", "bug_hunt", "deviations",
    "tool_choices", "limitations", "mistakes", "explain", "glossary_and_next",
]


# =============================================================================
def cover(D):
    d = D.d
    t = d.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade_cell(c, F_COVER); c.text = ""
    p = c.paragraphs[0]; no_space(p, 20, 2)
    r = p.add_run("PALISADE")
    r.bold = True; r.font.size = Pt(26); r.font.name = BODY_FONT; r.font.color.rgb = WHITE
    p2 = c.add_paragraph(); no_space(p2, 2, 2)
    r = p2.add_run("Engineering Log  ·  Milestone M1")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("The Inference Service: a real model, streaming, from the gateway to the GPU")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M1 - The Inference Service**"],
            ["Goal", "`curl -N` against the gateway streams tokens generated on the local GPU"],
            ["Result", "**Passed.** Verified live: a real streaming response, tokens generated on the RTX 3050, "
                       "through the gateway, through Kubernetes, through the CDI path"],
            ["Model", "Qwen3-0.6B, served as `palisade-small` by vLLM v0.28.0"],
            ["Where it runs", "In-cluster (the real target) **and** host Docker via compose (fast iteration)"],
            ["New code", "`docker/cuda-check`, `k8s/vllm.yaml`, `services/gateway/` (a full FastAPI slice), "
                        "`docker-compose.yml`"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("Same structure as M0, answering the same six standing questions.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**",
             "§4 What was built and **§5 How it was done** - the complete task-by-task walkthrough"],
            ["**2. What was done differently**, and why",
             "**§8 Deviations** - the model, and every parameter that changed from the plan under test"],
            ["**3. How it was done**",
             "§5, plus §6 - a single deep dive into three real, reproducible bugs found running vLLM "
             "in-cluster"],
            ["**4. What the limitations are**",
             "**§9 Limitations** - stated plainly, including the ones that will still be true in M2"],
            ["**5. Why this tool/approach over the alternatives**",
             "**§8 Tool choices**, and the milestone's four new ADRs (0003-0006)"],
            ["**6. Plain language and technical, both**",
             "Throughout, as **IN PLAIN LANGUAGE** / **TECHNICALLY** pairs."],
        ],
        widths=[2.1, 4.5],
    )

    D.callout("The one thing to take away from M1",
              "Every one of the three real bugs in §6 was invisible from the host-Docker spike in Task 2 "
              "and only appeared once the identical image and identical settings ran **inside a k3d node "
              "container** instead. 'It worked in Docker' and 'it works in Kubernetes' are different claims, "
              "and this milestone is the record of the gap between them.", "ok")


# =============================================================================
def what_it_was_for(D):
    D.h1("1. What M1 Was For")

    D.h2("1.1  The goal, stated simply")
    dual(D,
         "M0 proved a program that Kubernetes starts can **see** the graphics card. M1 asks a harder "
         "question: can that program actually **use** it to answer a real request, and can a normal HTTP "
         "client watch the answer arrive token by token, the way a modern chat product behaves?",
         "Serve an open-weight model through vLLM's OpenAI-compatible API on the RTX 3050, put a thin "
         "FastAPI gateway in front of it, and prove `curl -N .../v1/chat/completions` streams real tokens "
         "back - in-cluster, through the CDI path M0 built.")

    D.h2("1.2  Why this, and in this order")
    D.p("`nvidia-smi` only reads the driver. **Nothing in M0 ever ran a CUDA kernel.** Every task in M1 was "
        "ordered by the same rule that made M0 tractable: the cheapest test of the biggest unknown goes "
        "first, because it is the one that can force everything downstream to change.")
    D.table(
        ["#", "Task", "The unknown it tested", "Outcome"],
        [
            ["1", "Prove CUDA **compute**, not just visibility",
             "Does a kernel run through CDI at all?", "**Passed** - see §5.1"],
            ["2", "vLLM spike on host Docker",
             "Does the model fit in 4 GB VRAM?", "**Passed**, after two fallbacks - see §5.2"],
            ["3", "vLLM in the cluster",
             "Does host-Docker success transfer through the CDI path?",
             "**No, three times over** - the milestone's real content, §6"],
            ["4-5", "The gateway, containerised and tested",
             "Low risk, portable - deliberately last", "**Passed** - see §5.4-5.5"],
        ],
        widths=[0.35, 1.85, 2.55, 1.85],
    )
    D.callout("The principle carried over from M0",
              "**Sequence work by risk, cheapest test of the biggest unknown first.** Building the gateway "
              "before proving compute would have felt productive and told the project nothing about the two "
              "things that could actually derail M1.", "note")


# =============================================================================
def starting_point(D):
    D.h1("2. What Was True Going Into M1")
    D.p("M0 left a cluster that could see the GPU and a project plan rewritten to be goal-driven rather than "
        "scheduled. Nothing about the model-serving path had been touched.")

    D.table(
        ["What was checked", "What was found", "Why it mattered"],
        [
            ["Cluster state", "k3d cluster **stopped** (containers Exited, not deleted)",
             "Confirmed the docs/CONVENTIONS.md gotcha applies to a plain stop too, not only `wsl --shutdown`: "
             "`k3d cluster start` + `make gpu-cdi` were both needed before anything else."],
            ["`services/gateway/`", "Empty except `.gitkeep`",
             "A full FastAPI application had to be built from nothing, not extended."],
            ["Disk (E:)", "**61-78 GB free**, fluctuating across the milestone",
             "vLLM's image is ~9 GB compressed / ~29 GB unpacked. Two copies (host Docker + in-cluster) was "
             "always going to be tight, and it was - see §6.1 and §9."],
            ["RAM (WSL2 cap)", "10 GB, per `.wslconfig`",
             "Directly caused a background-task memory kill during Task 3's image-import attempt - the "
             "reason that path was abandoned for a lower-memory alternative (§6.1)."],
            ["Model choice", "Qwen3-0.6B selected over Qwen2.5-0.5B (M0's placeholder)",
             "Current, Apache-2.0, most-used small model on Hugging Face at time of writing (21.5M downloads "
             "vs 5.9M) - and, as it turned out, one with a default \"thinking\" behaviour worth designing "
             "around (§3.4)."],
        ],
        widths=[1.15, 2.15, 3.3],
    )


# =============================================================================
def decisions(D):
    D.h1("3. Decisions Taken Before Writing Any Code")

    D.h2("3.1  Model: Qwen3-0.6B")
    dual(D,
         "Use the newest small model that is free to use commercially and that the most other people are "
         "already using - both make it easier to compare notes and trust the model isn't an outlier.",
         "Apache-2.0 licensed, ungated, and (per Hugging Face download counts at time of writing) the "
         "dominant small model, ahead of the M0 placeholder Qwen2.5-0.5B by roughly 4x.")

    D.h2("3.2  Where vLLM runs: both host Docker and in-cluster")
    dual(D,
         "Run the model twice, in two different places, on purpose: once the simple way (a single Docker "
         "container) to learn the model's own behaviour without Kubernetes as a variable, and once for real, "
         "inside the cluster, which is what the project is actually about.",
         "Task 2 is a host-Docker spike; Task 3 deploys the same image via `k8s/vllm.yaml`. "
         "`docker-compose.yml` defaults to gateway-only (pointed at the cluster's vLLM via port-forward) and "
         "only pulls a second ~9 GB image under `--profile full`, opt-in.")
    D.callout("Why not just the cluster",
              "Because when vLLM later failed in-cluster three separate times (§6), having already seen "
              "it succeed on host Docker with known-good settings was the only way to know the *cluster* was "
              "the variable that had changed, not the model or its configuration. The spike was cheap "
              "insurance against a much more confusing debugging session.", "ok")

    D.h2("3.3  Gateway scope: thin but complete")
    dual(D,
         "Build the full shape of a real gateway now - auth, policy, metrics, health checks - but keep each "
         "piece small. Rate limiting, a semantic cache and per-tenant budgets are real features that belong "
         "to a later milestone once there is a live service to protect.",
         "`services/gateway/app/` ships `auth.py`, `policy.py`, `upstream.py`, `observability.py`, and "
         "`routes/{health,chat}.py` - the seams M4 slots budgets and a cache into without a rewrite.")

    D.h2("3.4  Server-side request policy, decided the moment it was discovered")
    dual(D,
         "Qwen3, left alone, narrates its own reasoning before answering - a `<think>...</think>` block "
         "nobody asked for. The gateway turns this off by default, but a caller can still ask for it "
         "explicitly.",
         "Confirmed live in the Task 2 spike: an unmodified request to `palisade-small` produced a `<think>` "
         "block. `policy.py` now injects `chat_template_kwargs.enable_thinking = false` unless the caller "
         "already set it - see ADR 0006.")
    D.callout("A decision written the moment it was found, not after the fact",
              "docs/CONVENTIONS.md's standing rule is to write the ADR **at the moment of the decision**, while the "
              "alternatives are fresh. This is the cleanest example in M1: the `<think>` block appeared "
              "mid-spike, unplanned, and the fix went straight into `policy.py` and ADR 0006 rather than "
              "being smoothed into 'the gateway also handles formatting'.", "note")


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")

    D.h2("4.1  New files and directories")
    D.table(
        ["Path", "Purpose"],
        [
            ["`docker/cuda-check/`", "A tiny multi-stage image: `nvcc` compiles a real `vectorAdd` kernel in "
             "a devel stage, only the compiled binary ships. Verifies numeric results, not just \"it ran\"."],
            ["`k8s/cuda-check.yaml`", "The Job that runs it in-cluster - M1's first acceptance test."],
            ["`scripts/cuda-check.sh`, `make cuda-check`", "Build, import, run, diagnose - same shape as "
             "M0's `gpu-check.sh`."],
            ["`k8s/vllm.yaml`", "PVC + Deployment + Service for vLLM in-cluster. `strategy: Recreate`, a "
             "generous `startupProbe`, `emptyDir: Memory` for `/dev/shm`, `enableServiceLinks: false` (§6.3)."],
            ["`scripts/vllm-up.sh`, `make vllm-up/-logs/-down`", "Pulls the image **inside the node** rather "
             "than via `k3d image import` (§6.1), applies the manifest, waits for readiness."],
            ["`services/gateway/app/`", "`config.py`, `auth.py`, `policy.py`, `upstream.py`, "
             "`observability.py`, `routes/health.py`, `routes/chat.py`, `main.py` - the full slice, detailed "
             "in §5.4."],
            ["`services/gateway/tests/`", "17 tests (pytest + respx): auth, policy, streaming order, health, "
             "one GPU integration test skipped by default. 16 passed, 1 skipped."],
            ["`services/gateway/Dockerfile`, `.dockerignore`", "Multi-stage, non-root, base image pinned by "
             "digest."],
            ["`docker-compose.yml`", "Gateway-only default profile; `--profile full` adds a local vLLM."],
            ["`docs/adr/0003` - `0006`", "vLLM vs. alternatives; OpenAI-compatible API as strategy; no "
             "autoscaling on the model tier; server-side request policy."],
            ["`doctor.sh`", "Gained an E:-drive free-space check (Docker's real data lives there, not "
             "`$HOME`) and a non-blocking pointer to `make cuda-check`."],
        ],
        widths=[1.9, 4.7],
    )

    D.h2("4.2  What was proven, end to end")
    D.p("Every row below was checked by hand, live, against the running system - not inferred from a green "
        "test run.")
    D.table(
        ["Check", "Result"],
        [
            ["A real CUDA kernel executes through CDI, in-cluster",
             "**PASS** - `vectorAdd`, 1,048,576 elements, RTX 3050 sm_86, every element numerically verified"],
            ["vLLM fits in 4 GB VRAM (host Docker)",
             "**PASS** at `--gpu-memory-utilization 0.7` - ~3.4 GiB in use while serving"],
            ["vLLM fits in 4 GB VRAM (in-cluster)",
             "**PASS**, but only after §6's three fixes - `--kv-cache-memory-bytes=512M` was the one "
             "that actually closed it"],
            ["Gateway `/readyz` reflects real upstream health",
             "**PASS** - 200 with vLLM up, 503 with it down (tested both, unit and live)"],
            ["Auth rejects a bad key",
             "**PASS** - 401, and `palisade_auth_failures_total{reason=\"unknown_key\"}` incremented"],
            ["**The acceptance test**: `curl -N` streams real tokens from the local GPU",
             "**PASS** - through the gateway, through the Kubernetes Service, through vLLM, off the RTX "
             "3050, with no `<think>` block (policy.py working against the live model)"],
            ["Unit tests pass without a GPU",
             "**PASS** - 16 passed, 1 skipped, in 0.6s, from a fresh `.venv`"],
            ["TTFT tracked separately from total duration",
             "**PASS** - `palisade_time_to_first_token_seconds` populated, ~194 ms observed"],
        ],
        widths=[2.75, 3.85],
    )


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done")
    D.p("The five tasks, in the order they were run, with the actual commands.")

    D.h2("5.1  Task 1 - Proving CUDA compute, not just visibility")
    D.p("`docker/cuda-check/check.cu` allocates two device vectors, launches `vectorAdd`, copies the result "
        "back, and asserts every element against the CPU-computed expected value before printing PASS.")
    D.code(
        "# multi-stage build - nvcc and the devel toolchain never reach the shipped image\n"
        "FROM nvidia/cuda:12.8.1-devel-ubuntu24.04 AS build\n"
        "RUN nvcc -O2 -arch=sm_86 -o cuda-check check.cu   # sm_86 = RTX 3050 (Ampere)\n"
        "FROM nvidia/cuda:12.8.1-base-ubuntu24.04 AS final\n"
        "COPY --from=build /src/cuda-check /usr/local/bin/cuda-check"
    )
    D.p("Verified at every layer before trusting the in-cluster result: `docker run --gpus all` locally "
        "first, then imported into k3d and run as a Job with the same `runtimeClassName: nvidia` / "
        "`cdi.k8s.io/gpu` shape as M0's `gpu-check.yaml`.")
    D.code(
        "$ make cuda-check\n"
        "device:             NVIDIA GeForce RTX 3050 Laptop GPU\n"
        "compute capability:  8.6\n"
        "elements:            1048576\n"
        "PASS: 1048576 elements verified - a real CUDA kernel executed and\n"
        "      produced the correct numeric result through the CDI path."
    )

    D.h2("5.2  Task 2 - vLLM spike on host Docker")
    D.p("The least complex environment first, before adding Kubernetes as a variable.")
    D.code(
        "docker run -d --gpus all --shm-size 2g -p 8000:8000 \\\n"
        "  -e VLLM_WSL2_ENABLE_PIN_MEMORY=1 \\\n"
        "  -v hf-cache:/root/.cache/huggingface \\\n"
        "  vllm/vllm-openai:v0.28.0 \\\n"
        "  --model Qwen/Qwen3-0.6B --served-model-name palisade-small \\\n"
        "  --max-model-len 4096 --gpu-memory-utilization 0.7 --enforce-eager"
    )
    D.p("This took three attempts, not one - see the fallback table.")
    D.table(
        ["Attempt", "What happened", "Fix applied"],
        [
            ["1", "`ValueError: Free memory ... less than desired GPU memory utilization` at "
             "`--gpu-memory-utilization 0.85`", "Lowered to 0.7 - WSL2/the desktop already holds back part "
             "of the 4 GB card"],
            ["2", "`RuntimeError: UVA is not available`", "Added `VLLM_WSL2_ENABLE_PIN_MEMORY=1` - see the "
             "explanation in §6.2's sibling finding below"],
            ["3", "Started cleanly", "`/health` 200, `/v1/models` listed `palisade-small`, VRAM settled at "
             "~3.4 GiB, and a streaming completion produced a `<think>` block by default"],
        ],
        widths=[0.7, 3.05, 2.85],
    )
    D.callout("A finding that shaped Task 4, discovered here, not planned",
              "The unprompted `<think>` block from attempt 3 is the direct origin of `policy.py`'s "
              "`enable_thinking` default (§3.4, ADR 0006). It was not a feature designed up front; it "
              "was a live observation that immediately became a design decision.", "ok")

    D.h2("5.3  Task 3 - vLLM in the cluster")
    D.p("`k8s/vllm.yaml`: a PVC on `local-path` for the Hugging Face cache (so a restart does not "
        "re-download ~1.4 GiB of weights), a generous `startupProbe` (model load takes far longer than a "
        "liveness probe tolerates), `/dev/shm` as a `Memory` `emptyDir`, and `strategy: Recreate` instead of "
        "the default `RollingUpdate` - a rolling update would briefly want two pods wanting the same GPU "
        "(ADR 0005). This task is where the milestone's real debugging happened; the full account is "
        "§6.")

    D.h2("5.4  Task 4 - The gateway")
    D.p("A thin FastAPI slice, structured so M4's budgets and cache slot in without a rewrite.")
    D.table(
        ["Module", "Job", "Notable decision"],
        [
            ["`config.py`", "env-driven settings (pydantic-settings)", "Upstream URL defaults to the "
             "in-cluster Service name, so the container works unmodified in Kubernetes"],
            ["`auth.py`", "`Authorization: Bearer plsd_...` -> tenant", "Only the SHA-256 **hash** of an "
             "accepted key is ever held or compared - a memory/config dump yields no usable credential"],
            ["`policy.py`", "server-side request rewriting", "Pins the model name, clamps `max_tokens`, "
             "injects `enable_thinking: false` unless overridden - see ADR 0006"],
            ["`upstream.py`", "one long-lived `httpx.AsyncClient`, SSE relay", "Chunks are relayed straight "
             "through, unbuffered - buffering would silently turn TTFT into \"time to last token\""],
            ["`observability.py`", "request IDs, structured JSON logs, Prometheus metrics", "TTFT is its "
             "own histogram, separate from total duration - in a chat UI it is what a user actually feels. "
             "Logs record token counts and latency, never prompt content"],
            ["`routes/health.py`", "`/healthz`, `/readyz`", "`/healthz` never touches the upstream (a dead "
             "upstream must not restart a healthy gateway); `/readyz` does, and is what Kubernetes gates "
             "traffic on"],
            ["`routes/chat.py`", "`/v1/models`, `/v1/chat/completions`", "Both streaming and non-streaming; "
             "OpenAI-compatible on purpose (ADR 0004)"],
        ],
        widths=[1.1, 2.55, 3.05],
    )
    D.p("A real bug surfaced mid-build, not in the design: FastAPI 0.141 cannot infer a Pydantic response "
        "model from a `StreamingResponse | JSONResponse` return annotation and refuses to start the app. "
        "Fixed with `response_model=None` on that one route.")

    D.h2("5.5  Task 5 - Containerise, compose, test")
    D.code(
        "# builder installs into a venv; runtime copies only the venv + app source\n"
        "FROM python:3.12-slim@sha256:78387bc3... AS builder\n"
        "RUN python -m venv /venv && /venv/bin/pip install -r requirements.txt\n"
        "FROM python:3.12-slim@sha256:78387bc3... AS runtime\n"
        "RUN useradd --system --no-create-home palisade\n"
        "COPY --from=builder /venv /venv\n"
        "COPY app ./app\n"
        "USER palisade"
    )
    D.p("Verified non-root inside the built container (`docker exec ... whoami` -> `palisade`), then the "
        "real acceptance test, live: port-forward the cluster's vLLM to `localhost:8000`, run the gateway "
        "locally against it, and stream a completion through the whole stack.")
    D.code(
        "$ curl -N localhost:8081/v1/chat/completions \\\n"
        "  -H 'Authorization: Bearer plsd_...' \\\n"
        "  -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in exactly three words.\"}],\n"
        "       \"stream\":true,\"max_tokens\":30}'\n"
        "data: {...\"delta\":{\"content\":\"Hello\"}...}\n"
        "data: {...\"delta\":{\"content\":\"!\"}...}\n"
        "data: {...\"delta\":{\"content\":\" \\ud83c\\udf1f\"}...}\n"
        "data: [DONE]"
    )
    D.p("No `<think>` block this time - `policy.py` suppressing it against the live model, not just in a "
        "unit test. `/metrics` showed `palisade_time_to_first_token_seconds` populated (~194 ms) and "
        "`palisade_tokens_total{direction=\"completion\"}` incrementing.")


# =============================================================================
def bug_hunt(D):
    D.h1("6. Deep Dive - Three Bugs, One GPU, Zero of Them Guessable in Advance")
    D.p("Task 3 (vLLM in-cluster) is where nearly all of M1's real debugging happened. None of the three "
        "bugs below appeared in the Task 2 host-Docker spike, using the identical image and, for the first "
        "two, the identical settings. Each is the kind of finding that only shows up by actually running the "
        "thing end to end, which is the argument for doing exactly that before calling a milestone done.")

    D.h2("6.1  Bug 1 - `k3d image import` silently fails on a multi-arch image")
    dual(D,
         "The tool used to load vLLM's ~9 GB image into the cluster reported success while the image was "
         "not actually there. It took importing the image a second way to notice.",
         "`vllm/vllm-openai:v0.28.0` is a multi-arch manifest list (amd64 + arm64). On this "
         "containerd-snapshotter-backed Docker, `docker save` on that tag exports a *reference* to the "
         "arm64 sub-manifest even though only the amd64 layers were ever pulled locally. `k3d image import` "
         "(which shells out to `docker save | ctr images import`) then fails inside the node with "
         "`ctr: content digest sha256:2a7cde23... not found` - but still prints "
         "\"Successfully imported image(s)\", because that message reports the *pipeline* completing, not "
         "the content actually landing.")
    D.p("The fix that worked: skip `k3d image import` entirely and have the node's own containerd pull "
        "directly from the registry, restricted to one platform.")
    D.code(
        "docker exec k3d-palisade-server-0 \\\n"
        "  ctr -n k8s.io images pull --platform linux/amd64 docker.io/vllm/vllm-openai:v0.28.0"
    )
    D.p("This also turned out to be the lower-risk path for an unrelated reason: attempting the "
        "`docker save` (an ~8.6 GB tar) then `ctr images import` route was killed twice by the harness's "
        "low-memory guard mid-transfer, inside a 10 GB WSL2 RAM cap already shared with an unrelated "
        "active project's containers. The direct registry pull streams layer by layer and never holds the "
        "whole image in memory at once.")

    D.h2("6.2  Bug 2 - the same `--gpu-memory-utilization` that worked on host Docker, OOMs in-cluster")
    dual(D,
         "The exact settings that worked a moment earlier, in a plain Docker container, ran out of GPU "
         "memory every time inside Kubernetes - and lowering the settings further barely helped, which was "
         "the real clue.",
         "`--gpu-memory-utilization 0.7` (proven in §5.2) reproducibly hit "
         "`torch.OutOfMemoryError` in-cluster during KV-cache allocation. Lowering to 0.6, and separately "
         "halving `--max-model-len` to 2048, each barely moved the shortfall - every attempt died needing "
         "only 30-50 MiB more. A percentage-based budget that is genuinely too small responds proportionally "
         "to a 15% cut; one that barely moves despite a 15% cut, twice, is reading a skewed number somewhere, "
         "not simply running short.")
    D.table(
        ["Setting tried", "Result"],
        [
            ["`--gpu-memory-utilization 0.7`",
             "OOM: \"Tried to allocate 50.00 MiB ... 1.38 GiB is free\""],
            ["`--gpu-memory-utilization 0.6`",
             "OOM again: \"Tried to allocate 34.00 MiB ... 1.22 GiB is free\" - barely different"],
            ["`--max-model-len 2048` (context halved), `0.6` kept",
             "OOM again: \"Tried to allocate 34.00 MiB ... 1.05 GiB is free\" - still barely different"],
            ["`--kv-cache-memory-bytes=512M`",
             "**Fixed.** Bypasses the percentage calculation entirely and states the KV cache size directly"],
        ],
        widths=[2.9, 3.7],
    )
    D.callout("Reading the pattern, not just the error",
              "The lesson generalises past vLLM: when a proportional lever (a percentage, a fraction, a "
              "ratio) is turned down substantially and the failure barely changes, the model computing that "
              "proportion is probably wrong, not the proportion you chose. Bypassing the computed value with "
              "an explicit, absolute one is often faster than continuing to tune the lever.", "note")

    D.h2("6.3  Bug 3 - a Kubernetes Service named after its own app breaks it")
    dual(D,
         "Naming the Service \"vllm\", which felt like the obvious name, caused Kubernetes to quietly "
         "overwrite one of vLLM's own internal settings with garbage, crashing it - and the crash's error "
         "message pointed straight at vLLM's own code, not at Kubernetes, which is what made it easy to miss.",
         "Kubernetes injects `<SERVICE>_PORT`, `<SERVICE>_SERVICE_HOST`, etc. into every pod's environment "
         "for every Service visible to it (`enableServiceLinks`, on by default). The Service in "
         "`k8s/vllm.yaml` is named `vllm`; vLLM itself reads `VLLM_PORT` for its own internal IPC. The "
         "injected value - `tcp://10.43.154.30:8000`, a URI - is not a port number, and vLLM crashed with "
         "`ValueError: VLLM_PORT '...' appears to be a URI`.")
    D.p("The warning that should have been the giveaway appeared earlier and was dismissed as noise: "
        "`WARNING: Unknown vLLM environment variable detected: VLLM_SERVICE_HOST` (and five siblings). Most "
        "of those really were harmless - vLLM logs and ignores env vars it does not recognise. `VLLM_PORT` "
        "was not one of the harmless ones; it happened to collide with a name vLLM's own code reads.")
    D.code("enableServiceLinks: false   # on the pod spec - stops the injection entirely")
    D.callout("A dismissed warning that was actually the bug",
              "The general lesson: a batch of near-identical warnings is not evidence they are all "
              "equally safe to ignore. One of six \"unknown environment variable\" lines was the actual "
              "root cause of every subsequent crash on that attempt - it just wasn't the one that looked "
              "different from the others.", "warn")

    D.h2("6.4  Two more things that happened along the way")
    D.p("Neither is a vLLM bug, but both cost real time and both are new, confirmed docs/CONVENTIONS.md gotchas.")
    D.table(
        ["What happened", "Cause", "Fix"],
        [
            ["Docker's WSL integration socket vanished with **no explicit `wsl --shutdown`**",
             "A memory-pressure event during the Bug 1 tar-import attempt was enough on its own",
             "The already-documented toggle (`IntegratedWslDistros` off, restart, on, restart) - confirmed "
             "it also fires without the shutdown trigger docs/CONVENTIONS.md previously named as the cause"],
            ["CoreDNS stuck in `ContainerCreating`, `MountVolume.SetUp failed ... NodeHosts` missing",
             "A Docker crash interrupted `k3d cluster start` mid-way through injecting a key into the "
             "`coredns` ConfigMap",
             "`kubectl delete pod` does **not** fix it (the ConfigMap itself is short a key). A clean "
             "`k3d cluster stop` then `k3d cluster start` redoes the injection"],
        ],
        widths=[2.0, 2.4, 2.2],
    )


# =============================================================================
def deviations(D):
    D.h1("7. What Was Done Differently, and Why")
    D.table(
        ["#", "The plan said", "What was done instead", "Why"],
        [
            ["1", "Qwen2.5-0.5B (M0's placeholder)", "**Qwen3-0.6B**",
             "Current, Apache-2.0, and the dominant small model by download count at time of writing "
             "(§3.1)."],
            ["2", "`--gpu-memory-utilization 0.85`", "**0.7 on host Docker, then 0.6 + "
             "`--kv-cache-memory-bytes=512M` in-cluster**",
             "0.85 failed the free-memory check outright; the in-cluster environment then needed the "
             "explicit KV-cache override on top - §6.2."],
            ["3", "`k3d image import` for the vLLM image", "**`ctr images pull` directly inside the node**",
             "The former silently fails on this multi-arch image and is also higher peak memory - §6.1."],
            ["4", "Nothing said about `enableServiceLinks`", "**Set to `false` on the vLLM pod**",
             "A Service named after its app collided with vLLM's own `VLLM_PORT` env var - §6.3."],
            ["5", "`--disable-log-requests` (from the plan's draft command)", "**Dropped - flag no longer "
             "exists in v0.28.0**",
             "Superseded by `--enable-log-requests`, which already defaults to `False`. Verified against "
             "`vllm serve --help=all` rather than assumed from memory."],
        ],
        widths=[0.3, 1.7, 2.15, 2.15],
    )
    D.callout("A deviation worth more than the original plan",
              "Deviations 2-4 exist only because Task 3 was actually run against the real cluster instead of "
              "being assumed to work once Task 2 succeeded. That is the same lesson M0 learned from the GPU "
              "investigation: **the interesting engineering content lives in the gap between \"works in a "
              "simple environment\" and \"works in the real one.\"**", "ok")


# =============================================================================
def tool_choices(D):
    D.h1("8. Tool Choices - What Was Picked and What Was Rejected")
    D.p("Full reasoning for the model-server choice and the API-shape choice now lives in dedicated ADRs "
        "(0003, 0004) rather than only here, since both are decisions M2-M5 will keep referring back to.")
    D.table(
        ["Decision", "Chosen", "Rejected, and why"],
        [
            ["Model server", "**vLLM** (ADR 0003)",
             "**Ollama** - consumer-facing, not the production-inference story this project tells. "
             "**llama.cpp** - more VRAM-efficient, but a lighter operational surface than the project's "
             "later milestones need. **TGI** - closest competitor, but less documentation to verify pins "
             "against for a 4 GB card."],
            ["API shape", "**OpenAI-compatible** (ADR 0004)",
             "A bespoke API - would need its own client library and reference docs. Matching an existing, "
             "already-documented standard means a caller changes a base URL and a key, nothing else."],
            ["GPU image storage (in-cluster)", "**Direct node-side `ctr` pull**",
             "**`k3d image import`** - silently fails on vLLM's multi-arch manifest (§6.1)."],
            ["Model tier scaling", "**None - single replica** (ADR 0005)",
             "**A CPU-based HorizontalPodAutoscaler** - would scale on a signal (CPU) that has nothing to do "
             "with the real bottleneck (VRAM), and a second replica cannot get a second GPU here anyway."],
            ["Request policy enforcement", "**Server-side, in the gateway** (ADR 0006)",
             "**Leaving it to callers/client libraries** - a caller could always skip a client-side "
             "convenience; the whole point of `enable_thinking`, `max_tokens` and model pinning is that "
             "they cannot be opted out of."],
            ["Test isolation", "**respx**, mocking the upstream", "**A real vLLM in CI** - needs a GPU, "
             "which CI does not have; the one real-model test exists but is skipped by default."],
        ],
        widths=[1.4, 1.5, 3.65],
    )


# =============================================================================
def limitations(D):
    D.h1("9. Limitations of This Setup")
    D.table(
        ["Limitation", "What it means in practice", "Honest position"],
        [
            ["**One GPU, one replica, no autoscaling**",
             "Throughput on this hardware has a hard ceiling. A CPU-based HPA would not even help - it "
             "measures the wrong resource.",
             "Deliberate (ADR 0005). Load management here is admission control and load shedding at the "
             "gateway, not orchestration - and that is a more interesting engineering problem to have "
             "solved than \"we added an HPA.\""],
            ["**`--kv-cache-memory-bytes=512M` is a manually chosen number, not derived**",
             "It comfortably covers `max-model-len=4096` for a 0.6B model, but was not computed from a "
             "formula - it was picked to have generous headroom after the percentage-based approach proved "
             "unreliable in this environment.",
             "Honest position: good enough for a single small model on this card. Revisit with a real "
             "formula (per-token KV-cache size × max sequences × max length) before trusting this "
             "number on a different model or GPU."],
            ["**No GPU test in CI**",
             "The one test that talks to a real model server is skipped unless "
             "`PALISADE_RUN_GPU_TESTS=1` is set explicitly, since CI runners do not have this GPU.",
             "Correct trade-off for now. 16 of 17 tests exercise real logic (auth, policy, streaming order, "
             "readiness) against a mocked upstream and need no GPU at all."],
            ["**Disk margin stayed thin all through Task 3**",
             "E: dropped as low as ~14 GB free mid-milestone while both a host-Docker copy and an in-cluster "
             "copy of vLLM briefly coexisted.",
             "Resolved by deleting the now-redundant host-Docker copy once Task 2's findings were recorded. "
             "`doctor.sh` now warns below 40 GB free and fails below 20 GB, so this is caught early instead "
             "of as a surprise mid-pull next time."],
            ["**The gateway has no rate limiting or per-tenant budgets yet**",
             "Any authenticated caller can currently make as many requests as the single model can queue.",
             "Explicitly out of scope for M1 by design (§3.3) - this is M4's job, and the seams "
             "(`auth.py`, `policy.py`) are already shaped for it."],
            ["**API keys live in one env var, not a real secret store**",
             "Fine for one operator; nothing here is designed for issuing or revoking individual keys "
             "without a redeploy.",
             "Deliberate for M1. Only the SHA-256 hash is ever held, so the exposure if this env var leaked "
             "is limited to a hash, not a usable credential. Moves to Redis in M4."],
        ],
        widths=[1.75, 2.35, 2.5],
    )


# =============================================================================
def mistakes(D):
    D.h1("10. Mistakes Made, and What They Cost")
    D.table(
        ["What went wrong", "Cost", "What prevents a repeat"],
        [
            ["**Trusted `k3d image import`'s success message.**",
             "Two failed deploy attempts before checking `crictl images` directly inside the node",
             "The same M0 lesson, recurring: verify state, not the report. `scripts/vllm-up.sh` now checks "
             "`crictl images` before deciding whether to pull at all."],
            ["**Dismissed a batch of near-identical warnings as uniformly harmless.**",
             "One extra failed deploy attempt before reading `VLLM_PORT`'s warning as distinct from its five "
             "siblings",
             "Recorded as a named pattern in §6.3 - a batch of similar-looking warnings is not evidence "
             "they are all equally safe."],
            ["**Tuned a percentage lever twice before questioning the percentage calculation itself.**",
             "Two OOM cycles (0.7 -> 0.6 -> halved context) before trying `--kv-cache-memory-bytes` directly",
             "The generalised lesson from §6.2: if turning a proportional setting down substantially "
             "barely changes a failure, suspect the thing computing the proportion, not the proportion "
             "chosen."],
        ],
        widths=[2.6, 2.0, 2.0],
    )
    D.callout("The pattern across all three",
              "Every one is a version of the same M0 lesson, applied at a different layer: **a tool's own "
              "report of success or a plausible-looking warning is not the same as the state actually being "
              "correct.** `crictl images`, a specific error string, and a percentage-vs-absolute setting "
              "were each the fact that mattered, once actually checked.", "ok")


# =============================================================================
def explain(D):
    D.h1("11. Design Rationale - Questions Answered")
    _qa(D, [
        ("Why prove CUDA compute before pulling a 9 GB model image?",
         "Cost-to-discover-late. A purpose-built kernel test costs a few hundred megabytes and a few "
         "seconds; a broken CDI path discovered only after a 9 GB pull would waste far more time isolating "
         "whether the problem was vLLM, the model, or the platform underneath both."),
        ("Why run vLLM on host Docker at all, if the cluster is the real target?",
         "To remove Kubernetes as a variable while learning the model's own behaviour - the `<think>` block, "
         "the actual VRAM footprint, the correct `VLLM_WSL2_ENABLE_PIN_MEMORY` fix. When the cluster then "
         "failed differently, it was immediately clear the cluster path itself had to be the cause, not the "
         "model or its settings."),
        ("`k3d image import` said it succeeded. How did you find out it hadn't?",
         "The Deployment came up with `imagePullPolicy: IfNotPresent` and immediately failed to find the "
         "image. Checking `crictl images` directly inside the node showed vLLM was simply absent, despite "
         "the tool's own \"Successfully imported\" message - which, read literally, only describes the "
         "import pipeline completing, not the content landing."),
        ("Why does `--kv-cache-memory-bytes` fix something `--gpu-memory-utilization` couldn't?",
         "The utilization flag asks vLLM to compute a KV-cache size as a percentage of a reported total VRAM "
         "figure. If that total (or the free-memory snapshot it is measured against) is itself off inside "
         "the nested k3d-node-container CDI path, every percentage computed from it inherits the error. "
         "Stating the KV-cache size directly, in bytes, removes that calculation from the picture entirely."),
        ("How did naming a Service \"vllm\" break vLLM?",
         "Kubernetes injects a `<SERVICE>_PORT` environment variable (and several siblings) into every pod "
         "for every Service it can see - a decades-old Docker-links-era convention still on by default. vLLM "
         "reads `VLLM_PORT` itself for internal process coordination, so the two collided: vLLM received a "
         "Kubernetes-generated URI where it expected a plain integer, and crashed."),
        ("Why is there only one vLLM replica?",
         "There is one GPU, and CDI does not participate in Kubernetes' resource accounting the way "
         "`nvidia.com/gpu` requests would - a second replica could not actually get a second GPU. Scaling "
         "answers here are admission control and load shedding at the gateway, not more pods (ADR 0005)."),
        ("Why match the OpenAI API shape instead of designing something Palisade-specific?",
         "It is the de facto standard every mainstream client library and eval harness already speaks. A "
         "caller changes a base URL and a key, nothing else - and Palisade never has to design, document, or "
         "maintain its own request/response reference (ADR 0004)."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("12. Glossary - Terms Introduced in M1")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**UVA**", "Unified Virtual Addressing - a CUDA feature letting host and device share address "
             "space for zero-copy memory. vLLM v0.28's engine requires it; WSL2 disables it by default."],
            ["**KV cache**", "The per-request memory a transformer model keeps so it doesn't recompute "
             "earlier tokens' attention state on every new token. Usually the largest consumer of VRAM "
             "during serving, alongside the model weights."],
            ["**TTFT**", "Time to first token - how long a caller waits before the first piece of a "
             "streamed response arrives. Tracked separately from total response time because it is what a "
             "user actually perceives as \"fast\" or \"slow.\""],
            ["**SSE (Server-Sent Events)**", "A simple HTTP streaming format - the server sends "
             "`data: ...\\n\\n` lines as they become available. What `stream: true` uses in the OpenAI Chat "
             "Completions API."],
            ["**Manifest list**", "A single image tag that actually points at several platform-specific "
             "images (e.g. amd64 and arm64). Pulling it fetches only the layers for your platform, but tools "
             "that re-export the tag can still reference the platforms never pulled."],
            ["**`enableServiceLinks`**", "A Kubernetes pod-spec field controlling whether Docker-links-style "
             "`<SERVICE>_*` environment variables are injected for every visible Service. On by default."],
            ["**Admission control**", "Deciding whether to accept a request at all, before doing any work - "
             "as opposed to accepting everything and hoping capacity keeps up."],
            ["**Load shedding**", "Deliberately rejecting or failing requests fast under overload, rather "
             "than accepting more work than can be completed in reasonable time."],
        ],
        widths=[1.5, 5.1],
        size=9.3,
    )

    D.h1("13. Open Items Going Into M2")
    D.table(
        ["Item", "Status", "Action"],
        [
            ["`--kv-cache-memory-bytes` chosen by feel, not formula", "Working, unverified at scale",
             "Fine for one small model on this card - revisit with a real per-model formula before trusting "
             "it elsewhere."],
            ["No hash-pinned dependencies yet", "Exact-pinned only",
             "M2 adds `pip-compile --generate-hashes` and a Syft SBOM on top of `requirements.txt`."],
            ["GitHub token lacks `workflow` scope", "Known, user action required",
             "`gh auth refresh -h github.com -s workflow` needed before M2's CI workflow files can be pushed."],
            ["No rate limiting or per-tenant budgets", "Deliberately deferred",
             "M4, per ADR 0006's stated seam in `policy.py`."],
        ],
        widths=[1.9, 1.55, 3.05],
    )
    D.spacer(4)
    D.callout("Where M2 goes",
              "**M2 - Supply chain & CI/CD.** Trivy as a gate, Syft SBOMs, cosign keyless signing over GitHub "
              "OIDC, and hash-pinned dependencies - turning the gateway image built in this milestone into "
              "one with a verifiable, signed provenance chain.", "note")
