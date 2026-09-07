# 3. vLLM over alternatives

- **Status:** Accepted

## Context

M1 needs a model server that exposes an OpenAI-compatible API, runs on a
single consumer GPU with 4 GB of VRAM, and is worth having on a DevOps
portfolio - something a hiring manager at an AI company will recognise as
the real production tool, not a toy. The realistic options were vLLM,
Ollama, llama.cpp (server mode), and Hugging Face TGI.

## Decision

**vLLM.** It is what production LLM-serving stacks at AI companies actually
run, its OpenAI-compatible server is the reason docs/adr/0004 is possible at
all, and it exposes the exact levers M1 ended up needing under WSL2's
constraints - `--gpu-memory-utilization`, `--kv-cache-memory-bytes`,
`--enforce-eager`, `VLLM_WSL2_ENABLE_PIN_MEMORY` - as first-class,
documented settings rather than something to patch around.

**Rejected:**

- **Ollama** - excellent for local single-user chat, but its API surface and
  its target audience are both consumer-facing, not the production-inference
  story this project is telling. Less to demonstrate against.
- **llama.cpp server** - the most VRAM-efficient of the four (GGUF
  quantisation would have made the 4 GB ceiling a non-issue) and a
  legitimate choice for genuinely resource-constrained deployment. Rejected
  because the project's DevSecOps arc (supply chain, GitOps, budgets, SLOs
  in M2-M5) is written against an inference server with the operational
  surface vLLM has - metrics, structured request handling, a real scheduler
  - not a lighter-weight C++ server built for a different use case.
- **TGI (Hugging Face Text Generation Inference)** - closest competitor to
  vLLM on paper. Rejected on ecosystem weight for a 4 GB card: vLLM's
  Qwen3/small-model support and its WSL2-specific escape hatches (found the
  hard way in this milestone) were better documented and easier to verify
  against upstream sources before committing.

## Consequences

- Every WSL2/CDI-path quirk found in M1 (pinned memory, KV-cache
  auto-sizing, the `enableServiceLinks` collision) is now a documented,
  reproducible fact about *this specific* server on *this specific* stack -
  valuable content for the project's documentation, but it means M1's
  troubleshooting surface is vLLM-shaped, not generic.
- If the hardware ever changes to something with real multi-GPU capacity,
  vLLM's tensor-parallel and continuous-batching machinery scales up without
  a server swap - unlike Ollama or llama.cpp, which would likely need
  replacing at that point anyway.
- What would change this answer: genuinely VRAM-starved hardware (well under
  4 GB) would tip the balance to llama.cpp's quantisation story; a pure
  single-user local-chat use case (no gateway, no multi-tenant story) would
  tip it to Ollama.
