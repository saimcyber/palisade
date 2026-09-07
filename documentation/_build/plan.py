# -*- coding: utf-8 -*-
"""Content for the Palisade project plan document.

Goal-driven, not schedule-driven: milestones are defined by what must be true
for them to be finished, never by how long they should take.
"""
from docx_kit import *   # noqa: F403

# Rendered in this order. build.py uses a module's SECTIONS when present.
SECTIONS = ["cover", "context", "how_it_works", "architecture", "stack",
            "milestones", "risks", "verification", "cost"]



def cover(D):
    d = D.d
    t = d.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade_cell(c, F_COVER); c.text = ""
    p = c.paragraphs[0]; no_space(p, 26, 2)
    r = p.add_run("PALISADE")
    r.bold = True; r.font.size = Pt(38); r.font.name = BODY_FONT; r.font.color.rgb = WHITE
    p2 = c.add_paragraph(); no_space(p2, 0, 4)
    r = p2.add_run("A Secure, Self-Hosted LLM Inference Platform")
    r.font.size = Pt(15); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 6, 24)
    r = p3.add_run("GitOps-delivered LLM serving with a verified supply chain,\n"
                   "per-tenant token budgets, and policy enforcement at admission.")
    r.italic = True; r.font.size = Pt(10.5); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(12)
    D.p("PROJECT PLAN", size=9.5, bold=True, color=SLATE, after=2)
    D.p("Portfolio project for DevOps / DevSecOps Engineer roles at AI companies",
        size=10, color=SLATE, after=12)

    D.table(
        ["Field", "Detail"],
        [
            ["Project", "**Palisade**"],
            ["Repository", "https://github.com/saimcyber/palisade (public)"],
            ["Target roles", "DevOps Engineer / DevSecOps Engineer / Platform Engineer / SRE at AI companies"],
            ["Structure", "Six milestones, **M0-M5**, each finished when its acceptance test passes"],
            ["Cloud budget", "**$0.** Free-tier services only. No billable compute is ever provisioned."],
            ["Hardware", "NVIDIA RTX 3050 Laptop (4 GB VRAM), 16 GB RAM, Windows 11 + WSL2 Ubuntu 24.04"],
            ["Deliverables", "A public repository, a live demo URL, a short demo video, and a set of engineering documents"],
        ],
        widths=[1.4, 5.2],
    )

    D.spacer(6)
    D.callout(
        "This plan has no schedule, and that is deliberate",
        "There are no dates, no day allocations and no duration estimates anywhere in this "
        "document. **Progress is measured by goals met, not by time elapsed.** A milestone is "
        "finished when its acceptance test passes and its documentation is written - whether that "
        "takes an evening or a month. Estimates on a solo project done around other commitments "
        "create false pressure and invite shortcuts in exactly the places that matter: "
        "verification, security and writing things down.", "note")


def context(D):
    D.h1("1. Context and Goal")

    D.h2("1.1  What this is for")
    D.p("One flagship project to put in front of AI companies when applying for DevOps and "
        "DevSecOps roles. Every decision is judged against a single question: **does this make the "
        "project more convincing to a hiring manager, and can it be defended in an interview?**")

    D.h2("1.2  Why not the usual MLOps pipeline")
    D.p("The standard portfolio project for this role is: train a small scikit-learn model, wrap it "
        "in FastAPI, containerise it, deploy to managed Kubernetes, add Prometheus and Grafana. It "
        "is a reasonable exercise, but **thousands of candidates have submitted a near-identical "
        "version of it**, and it does not describe the work an AI company actually needs done.")
    D.p("Palisade is built around the problems that genuinely consume a DevOps engineer's week at an "
        "AI company:")

    D.table(
        ["The real problem at an AI company", "What Palisade demonstrates"],
        [
            ["**GPUs are the entire budget.** A single idle GPU costs more than a whole web "
             "application's infrastructure. Utilisation and queueing are the job.",
             "GPU-backed serving with vLLM, queue-depth metrics, deliberate load shedding, GPU/VRAM "
             "dashboards"],
            ["**Nobody knows which customer is burning the money.** Token spend is invisible until "
             "the invoice arrives.",
             "Per-tenant token budgets enforced *before* the GPU is touched, plus a cost-attribution "
             "dashboard"],
            ["**Model weights are an untrusted binary** downloaded from the internet and executed "
             "with GPU access.",
             "Checksum and signature verification in an init container - the model does not load if "
             "it does not match"],
            ["**Prompts are a new, unfiltered attack surface** no traditional web firewall "
             "understands.",
             "An input guard at the gateway, labelled block metrics, and a written STRIDE threat "
             "model for an LLM platform"],
            ["**Anyone with cluster access can push anything to production**, untraceably.",
             "Git is the only path to production, and the cluster itself rejects unsigned images at "
             "admission"],
            ["**API keys leak constantly** - in CI logs, repositories, chat messages.",
             "No long-lived credentials anywhere: GitHub OIDC federation to AWS, encrypted secrets "
             "in Git"],
        ],
        widths=[3.3, 3.3],
    )

    D.h2("1.3  The sentence this is all for")
    D.callout("For the CV",
              "Built and operated a self-hosted LLM inference platform on Kubernetes with a signed, "
              "SBOM-attested supply chain, Kyverno admission policy, GitOps delivery via Argo CD, "
              "per-tenant token budgeting and cost attribution, and SLO-backed observability - "
              "running on GPU hardware at zero cloud spend.", "ok")


def how_it_works(D):
    D.h1("2. How Palisade Works")
    D.p("The whole system in plain terms before any technical detail. The per-milestone documents in "
        "`documentation/` expand on each part as it is built.", color=SLATE)

    D.h2("2.1  The one-paragraph version")
    D.callout(
        "Palisade in one paragraph",
        "A language model runs on a local GPU. Nobody is allowed to talk to it directly. Every "
        "request goes through a **gateway** that checks who you are, whether you are going too "
        "fast, whether you have budget left, and whether your request looks malicious - and only "
        "then passes it to the model. Everything runs on **Kubernetes**. The only way to change "
        "what is running is to **change a file in Git**; a reconciler notices and applies it. "
        "Before anything starts, a **policy engine** checks the container was built by the official "
        "pipeline and signed - if not, it is refused. While it runs, **Prometheus** collects "
        "numbers and **Grafana** draws the graphs showing whether it is healthy, how fast it is, "
        "and which customer is spending the money.", "note")

    D.h2("2.2  The analogy: a metered utility")
    D.table(
        ["In the utility", "In Palisade", "What it does"],
        [
            ["The power station", "**vLLM** on the GPU",
             "The only thing that generates the product. Expensive, finite, and the business depends "
             "on keeping it busy but not overloaded."],
            ["The front desk and meter", "**The gateway**",
             "Checks identity, reads the meter, refuses you if overdrawn, logs everything. No "
             "customer touches the power station directly."],
            ["The ledger", "**Redis**",
             "Remembers who used how much, who is going too fast, and stores answers already "
             "produced so the station does not repeat work."],
            ["The operations crew", "**Kubernetes** (k3d)",
             "Keeps the right machines running and restarts them when they fail."],
            ["The single locked door", "**Argo CD**",
             "Nothing enters except through this door, and it only opens for something written in "
             "Git."],
            ["The guard checking IDs", "**Kyverno**",
             "Inspects every container before it starts. No valid signature from the official "
             "pipeline means it does not come in."],
            ["The fuel inspection", "**Init container verification**",
             "Model weights are checked against a known checksum and signature before they are "
             "loaded."],
            ["The control room", "**Prometheus + Grafana**",
             "Live readings of load, speed, consumption per customer, and every blocked attempt."],
            ["The perimeter fence", "**NetworkPolicies**",
             "The power station has no outbound line at all. Even if sabotaged, it could not call "
             "anyone."],
        ],
        widths=[1.3, 1.5, 3.8],
    )

    D.h2("2.3  What happens when someone asks the AI a question")
    D.p("The request path, in order. **Six independent checks happen before a single GPU cycle is "
        "spent**, each cheaper than the one after it - so the expensive resource is protected by a "
        "series of progressively more expensive filters.")
    for i, (t, b) in enumerate([
        ("Arrives", "HTTP POST to `/v1/chat/completions` with a bearer key. The API is "
                    "OpenAI-compatible, so any existing client works by changing one line."),
        ("Reaches the cluster", "Cloudflare Tunnel pulls it in over an outbound connection - no open "
                                "port, no public IP - then Traefik routes it."),
        ("Who are you?", "The gateway hashes the key and looks it up. Keys are never stored in "
                         "plaintext, so a database dump yields no working credentials."),
        ("How fast?", "Sliding-window rate limit per tenant. Over it means `429` with `Retry-After`."),
        ("Can you afford it?", "The prompt's token cost is estimated against the tenant's remaining "
                               "budget. **If they cannot afford it, the request is rejected before "
                               "the GPU is touched.**"),
        ("Is it safe?", "Injection heuristics, PII redaction, length clamps. Every block is a "
                        "labelled metric. Documented as defence in depth, not a solved problem."),
        ("Answered before?", "A cache keyed on model, prompt, parameters **and tenant**. The tenant "
                             "is in the key deliberately: without it one customer could receive "
                             "another's cached answer."),
        ("Ask the model", "vLLM batches it with other in-flight requests and streams tokens back. If "
                          "its queue is saturated, the gateway sheds load cleanly rather than letting "
                          "everything time out."),
        ("Settle up", "Real token counts recorded, budget decremented, cost computed, one structured "
                      "audit line written - containing the request ID and tenant, but never the "
                      "prompt itself."),
    ], 1):
        par = D.d.add_paragraph()
        par.paragraph_format.left_indent = Inches(0.30)
        par.paragraph_format.space_before = Pt(4)
        par.paragraph_format.space_after = Pt(1)
        par.paragraph_format.keep_with_next = True
        r = par.add_run(f"{i}.  {t}")
        r.bold = True; r.font.size = Pt(10.3); r.font.name = BODY_FONT; r.font.color.rgb = TEAL_D
        bb = D.d.add_paragraph()
        bb.paragraph_format.left_indent = Inches(0.30)
        bb.paragraph_format.space_after = Pt(3)
        add_rich(bb, b, size=10.2)

    D.h2("2.4  What happens when someone attacks it")
    D.p("This table is what separates a DevSecOps portfolio from a DevOps one. Each row is a real "
        "attack, the specific control that stops it, and where it can be *seen* being stopped.")
    D.table(
        ["Attack", "What stops it", "Where you see it"],
        [
            ["**A customer API key leaks**",
             "Keys stored only as hashes; per-tenant rate limit and hard token budget cap the "
             "damage. Revocation is deleting one key.",
             "Security dashboard: auth failures, then the budget wall"],
            ["**Prompt injection**",
             "Pattern guard at the gateway; the system prompt is server-side so a client cannot "
             "replace it. Explicitly a partial mitigation.",
             "`guard_blocks_total{reason=\"injection\"}`"],
            ["**Poisoned model weights**",
             "An init container verifies checksum and signature before vLLM starts. A mismatch means "
             "the pod never runs.",
             "Pod stuck in Init with an explicit reason"],
            ["**A malicious dependency reaches the image**",
             "Trivy gates the build in CI; Kyverno independently refuses unsigned images at "
             "admission. Two controls, two trust domains.",
             "Failed CI run, or an admission-denial event"],
            ["**The model tries to exfiltrate data**",
             "The vLLM pod has **zero egress**. Even fully compromised, it has nowhere to send "
             "anything.",
             "Exec into the pod, attempt any outbound call, watch it fail"],
            ["**Token-exhaustion denial of service**",
             "Pre-flight budget checks reject before GPU work begins; the queue is bounded and "
             "excess load is shed.",
             "SLO dashboard holding target while load sheds"],
            ["**Someone bypasses CI and applies by hand**",
             "Kyverno rejects the unsigned image; Argo CD self-heal reverts drift.",
             "Argo shows OutOfSync, then reverts"],
            ["**A secret is committed to Git**",
             "Secrets are SOPS-encrypted at rest, so the committed file is useless on its own.",
             "The encrypted file is public and harmless"],
        ],
        widths=[1.85, 2.85, 1.9],
    )


def architecture(D):
    D.h1("3. Architecture")
    D.code(r"""
                              git push
                                 |
     +---------------------------v-----------------------------------+
     |                     GITHUB ACTIONS (CI)                        |
     |  lint -> unit tests -> build (multi-stage, non-root)           |
     |  -> Trivy scan (fail on HIGH/CRITICAL) -> Syft SBOM            |
     |  -> cosign keyless sign (Sigstore) -> push ghcr.io             |
     |            +---- OIDC, no static keys ----> AWS  S3 / IAM      |
     +---------------------------+-----------------------------------+
                                 | automated digest bump (PR)
     +---------------------------v-----------------------------------+
     |              ARGO CD  -  GitOps reconciler (in cluster)        |
     +---------------------------+-----------------------------------+
                 +---------------v----------------+
                 |     KYVERNO  admission gate    |
                 |  verifyImages: unsigned = DENY |
                 |  no :latest . non-root . limits|
                 +---------------+----------------+
   Internet --> Cloudflare Tunnel --> Traefik Ingress
                                          |
                              +-----------v------------+
                              |    PALISADE-GATEWAY    |        +---------+
                              |  1 tenant API keys     |<------>|  REDIS  |
                              |  2 rate limit          |        | budgets |
                              |  3 token budget        |        | + cache |
                              |  4 prompt guard        |        +---------+
                              |  5 response cache      |
                              |  6 audit log + metrics |
                              +-----------+------------+
                                          |  NetworkPolicy: gateway -> vLLM only
                              +-----------v------------+
                              |     vLLM  (on GPU)     |   Qwen2.5-0.5B-Instruct
                              |  initContainer:        |<--- S3 (model artifacts)
                              |  verify SHA256 + sig   |
                              |  egress: NONE          |
                              +------------------------+

   PROMETHEUS  <- scrapes gateway, vLLM, GPU exporter, kube-state
   GRAFANA     -> 4 dashboards:  SLO . GPU & Model . Cost & Tenancy . Security
""", size=7.4)

    D.h2("3.1  Two decisions worth defending")
    D.p("**The gateway is the product; the model is a swappable backend.** The model is sized to a "
        "laptop GPU and that is deliberately uninteresting. Every capability with commercial value - "
        "auth, budgets, caching, guardrails, audit, observability - lives in the platform layer and "
        "is model-agnostic. Given a cluster of H100s, exactly one Deployment changes.")
    D.p("**vLLM does not autoscale, and the project says so plainly.** One GPU means one replica. "
        "The honest response is not a meaningless CPU-based autoscaler on a GPU-bound workload; it "
        "is what real platforms do under GPU scarcity - a bounded queue, admission control by token "
        "budget, and graceful load shedding. Explaining why there is *no* HPA here is a stronger "
        "answer than showing one that would never fire correctly.")


def stack(D):
    D.h1("4. Technology Stack")
    D.table(
        ["Layer", "Choice", "Why this, and not the obvious alternative"],
        [
            ["Model serving", "**vLLM**, Qwen2.5-0.5B-Instruct",
             "The production standard at AI companies; Ollama is a developer tool. Its "
             "OpenAI-compatible API is what makes the gateway a drop-in replacement."],
            ["Gateway", "**FastAPI** + Redis",
             "Writing it rather than configuring LiteLLM is the point - it is the file an "
             "interviewer will actually open."],
            ["Cluster", "**k3d** (k3s in Docker)",
             "Fits the RAM budget, creates and destroys in one command, and is a genuine conformant "
             "Kubernetes API."],
            ["Infrastructure as code", "**Terraform**",
             "AWS (S3, IAM, OIDC) plus in-cluster add-ons through the Helm provider. One tool, one "
             "state model, one review process."],
            ["Delivery", "**Argo CD**",
             "Among the most requested skills on DevOps job descriptions, and it makes 'Git is the "
             "only path to production' literally true."],
            ["Policy", "**Kyverno**",
             "Policies in YAML rather than learning Rego, and `verifyImages` produces the best live "
             "demonstration in the project."],
            ["Supply chain", "Trivy, Syft, **cosign** (keyless)",
             "Keyless signing through GitHub OIDC means there is no private key to store, rotate or "
             "explain away."],
            ["Secrets", "**SOPS + age**",
             "Encrypted secrets live safely in Git, which GitOps requires. Vault would consume "
             "around a gigabyte of RAM for no additional signal at this scale."],
            ["Observability", "Prometheus, Grafana, DCGM exporter",
             "Deliberately slim with short retention; `kube-prometheus-stack` is far too heavy for "
             "the hardware, and that constraint is itself worth documenting."],
            ["Load testing", "**k6**",
             "Scriptable, runs in CI, and produces the latency percentiles the SLO document is built "
             "on."],
            ["Public access", "**Cloudflare Tunnel**",
             "Free, no public IP, no port forwarding, TLS included, outbound only."],
        ],
        widths=[1.05, 1.55, 4.0],
    )

    D.h2("4.1  Deliberately excluded")
    D.p("Each exclusion is an ADR in the repository. **Knowing what not to build is a senior "
        "signal**, and these are exactly the items a reviewer will otherwise ask about.")
    D.table(
        ["Excluded", "Reason"],
        [
            ["Service mesh (Istio / Linkerd)",
             "Would consume more memory than the workload, to solve problems a two-service system "
             "does not have. NetworkPolicies already provide the segmentation needed."],
            ["HashiCorp Vault",
             "SOPS covers the requirement at a fraction of the resource cost and keeps secrets "
             "inside the GitOps model rather than beside it."],
            ["Managed Kubernetes (EKS / GKE / AKS)",
             "Roughly $75 a month for the control plane alone, and it adds no new skill to the "
             "narrative. The cost model is documented instead."],
            ["Vector database / RAG",
             "An application concern, not a platform concern. It would dilute the DevOps story the "
             "project exists to tell."],
            ["A custom Kubernetes operator",
             "Significant work for a capability Helm plus Argo CD already covers here."],
            ["Multi-cloud or multi-region",
             "Complexity with no matching demonstration value at this scale."],
            ["Falco (runtime threat detection)",
             "Genuinely valuable but memory-hungry. Listed as a stretch goal rather than dropped "
             "silently."],
        ],
        widths=[1.6, 5.0],
    )


def milestones(D):
    D.h1("5. Milestones")
    D.p("Six milestones. Each is **finished when its acceptance test passes and its document is "
        "written** - not when a date arrives. They are ordered so that every one ends in something "
        "demonstrable: if work stops after any milestone, what exists is still coherent.",
        color=SLATE)

    D.table(
        ["", "Milestone", "The goal", "Status"],
        [
            ["**M0**", "Foundations", "A local Kubernetes cluster where a scheduled pod can drive the GPU", "**COMPLETE**"],
            ["**M1**", "The inference service", "A model served on the GPU behind an OpenAI-compatible gateway", "**NEXT**"],
            ["**M2**", "Supply chain and CI/CD", "Nothing ships that is not scanned, attested and signed", "Not started"],
            ["**M3**", "Kubernetes, GitOps, policy", "Git is the only path to production, and the cluster enforces it", "Not started"],
            ["**M4**", "Platform and observability", "Per-tenant budgets and cost visible on a dashboard", "Not started"],
            ["**M5**", "Resilience and proof", "Evidence it performs, survives failure, and can be understood", "Not started"],
        ],
        widths=[0.5, 1.5, 3.5, 1.1],
    )

    D.callout("What 'finished' means for every milestone",
              "Three things, all of them: **(1)** the acceptance command passes from a clean "
              "rebuild, not from a machine that happens to be in a good state; **(2)** any decision "
              "made along the way has an ADR; **(3)** the milestone document in `documentation/` is "
              "written - what was built, what differed from the plan, the limitations, and why each "
              "tool was chosen over its alternatives.", "note")

    # ---------------- M0
    D.h2("M0 - Foundations   (COMPLETE)")
    D.p("**Goal:** prove the hardest physical dependency works before building anything on top of it "
        "- that a program Kubernetes starts can use the laptop GPU.")
    D.table(
        ["Delivered", "Notes"],
        [
            ["GPU reachable from a scheduled pod",
             "Took three separate failures to achieve. The NVIDIA device plugin **cannot work under "
             "WSL2** (NVML is unsupported against `/dev/dxg`); CDI injection is used instead. Full "
             "write-up in ADR 0002."],
            ["Pinned toolchain + `make doctor`", "15 tools, 28 environment checks, exits non-zero so CI can gate on it"],
            ["Repository, Makefile, pre-commit", "All hooks passing, including gitleaks and shellcheck"],
            ["Cluster profiles", "`up-lite` / `up-full` - the full stack will not co-exist with a GPU workload in the RAM available"],
            ["Docker storage relocated", "The original drive could not hold the vLLM image"],
        ],
        widths=[2.0, 4.6],
    )
    D.p("**Acceptance (met):** `make down && make up && make gpu-check` reports "
        "`M0 ACCEPTANCE PASSED`; `make doctor` reports 28 passed, 0 failed.")

    # ---------------- M1
    D.h2("M1 - The inference service   (NEXT)")
    D.p("**Goal:** a real model answering real requests on the local GPU, behind the first version "
        "of the gateway.")
    D.bullet("vLLM serving Qwen2.5-0.5B-Instruct, sized to 4 GB of VRAM")
    D.bullet("`palisade-gateway` in FastAPI: `/healthz`, `/readyz`, `/v1/chat/completions`, `/metrics`, with streaming")
    D.bullet("Multi-stage Dockerfile, non-root user, pinned base digest")
    D.bullet("`docker-compose.yml` for a fast local loop that does not need Kubernetes")
    D.bullet("Unit tests for auth, budget arithmetic and guard rules, plus one integration test")
    D.p("**Acceptance:** `curl -N` against the gateway streams tokens generated on the local GPU.")

    # ---------------- M2
    D.h2("M2 - Supply chain and CI/CD")
    D.p("**Goal:** make it impossible to ship an artefact that has not been scanned, described and "
        "signed - and prove no long-lived cloud credential exists anywhere.")
    D.bullet("Terraform: S3 for model artifacts, S3 backend for state, GitHub OIDC provider, and an IAM role assumable **only** by this repository")
    D.bullet("A billing alarm set before any Terraform is written")
    D.bullet("GitHub Actions: lint, test, build, **Trivy gate** on HIGH/CRITICAL, **Syft SBOM**, **cosign keyless signature**, push to ghcr.io")
    D.bullet("Workflow hardened: least-privilege `permissions:`, third-party actions pinned to commit SHAs")
    D.bullet("`terraform plan` on pull requests, `apply` gated on merge")
    D.p("**Acceptance:** a green pipeline emits a signed image with an SBOM; `cosign verify` succeeds "
        "from the terminal; the GitHub repository contains **no stored AWS secrets**.")

    # ---------------- M3
    D.h2("M3 - Kubernetes, GitOps and policy")
    D.p("**Goal:** git becomes the only route to production, and the cluster itself enforces the "
        "rules rather than trusting the pipeline.")
    D.bullet("Helm chart: Deployments, Services, Ingress, ConfigMaps, PodDisruptionBudget")
    D.bullet("Probes done properly - the **startup probe** matters because the model takes time to load and a liveness probe alone would crash-loop it forever")
    D.bullet("Argo CD via the Terraform Helm provider; app-of-apps with auto-sync and self-heal")
    D.bullet("Kyverno: verify cosign signatures, block `:latest`, require non-root, require resource limits, drop all capabilities, read-only root filesystem")
    D.bullet("NetworkPolicies: default-deny; gateway to vLLM and Redis only; **no egress whatsoever from vLLM**")
    D.bullet("Model verification init container: pull weights, verify SHA-256 and signature, refuse to start on mismatch")
    D.bullet("SOPS + age encrypted secrets committed to the repository")
    D.p("**Acceptance:** a push to Git deploys itself - **and** an unsigned image is refused by the "
        "cluster with a readable reason. Record that refusal; it is the strongest single "
        "demonstration in the project.")

    # ---------------- M4
    D.h2("M4 - Platform features and observability")
    D.p("**Goal:** the platform becomes multi-tenant and legible - who is using it, what it costs, "
        "and whether it is healthy.")
    D.bullet("Hashed per-tenant API keys and sliding-window rate limits")
    D.bullet("**Token budgets**: pre-flight estimate before the GPU is touched, post-flight reconciliation against actual usage")
    D.bullet("Prompt guard: injection heuristics, PII redaction, clamps - each block a labelled metric")
    D.bullet("Response cache keyed **per tenant**, with hit rate and tokens saved measured")
    D.bullet("Prometheus, Grafana and a GPU exporter, slim enough to fit alongside the workload")
    D.bullet("Four dashboards: **SLO** (latency percentiles, error rate, time-to-first-token); **GPU & Model** (VRAM, utilisation, tokens/sec, queue depth); **Cost & Tenancy** (spend per tenant, budget burn-down); **Security** (blocks by reason, auth failures, admission denials)")
    D.bullet("Alert rules: SLO burn rate, GPU saturation, budget exhausted, injection-block spike, restart loop")
    D.bullet("Structured JSON audit logging with a request ID threaded through every hop - and prompt content deliberately excluded")
    D.p("**Acceptance:** traffic from two tenants shows divergent spend on the dashboard, and one "
        "hits its budget ceiling and receives `429` while the other is unaffected.")

    # ---------------- M5
    D.h2("M5 - Resilience, proof and storytelling")
    D.callout("Do not skip this milestone",
              "M0-M4 build the system. **M5 is what actually gets you hired.** Many repositories "
              "contain similar infrastructure; almost none contain a threat model, an SLO backed by "
              "real load-test numbers, and a blameless post-mortem. The infrastructure gets you "
              "shortlisted; the writing gets you the offer.", "danger")
    D.bullet("k6 load test ramping to saturation, run in CI")
    D.bullet("**Chaos day** - break it deliberately and take notes: kill vLLM mid-stream, exhaust VRAM, blackhole Redis, deploy a bad image")
    D.bullet("`README.md`: architecture diagram, quickstart, screenshots, and the admission-denial recording above the fold")
    D.bullet("`docs/ARCHITECTURE.md` plus the accumulated ADRs")
    D.bullet("`docs/THREAT-MODEL.md`: STRIDE for an LLM platform - model poisoning, prompt injection, token exhaustion as DoS, cross-tenant cache leakage, supply chain")
    D.bullet("`docs/SLO.md`: indicators, targets, error budget, and the measured numbers behind each")
    D.bullet("`docs/RUNBOOK.md`: the most likely alerts and the response to each")
    D.bullet("`docs/POSTMORTEM-001.md`: a blameless write-up of a real chaos-day failure")
    D.bullet("`docs/COST.md`: what this costs on real cloud, and the self-host versus hosted-API break-even")
    D.bullet("Cloudflare Tunnel demo, protected by a demo tenant with a hard budget cap")
    D.bullet("A short demo video: request, dashboard, unsigned deploy rejected, budget exhausted, chaos recovery")
    D.p("**Acceptance:** a stranger can understand the project without you in the room, and "
        "`git clone && make up` reproduces the platform on a clean machine.")


def risks(D):
    D.h1("6. Risks")
    D.p("Each risk has a response decided **now**, while calm - not at the point of failure.")
    D.table(
        ["Risk", "Likelihood", "Response decided in advance"],
        [
            ["GPU passthrough breaks after an update",
             "Medium",
             "**Already survived once.** The fallback is documented in ADR 0002: run vLLM as a host "
             "container and point an in-cluster Service with manual Endpoints at it. The gateway, "
             "policy, GitOps and observability layers are unaffected by which option is in use."],
            ["RAM exhausted once the full stack runs",
             "**High**",
             "Cluster profiles (`up-lite` / `up-full`), a capped WSL2 VM, slim Prometheus with short "
             "retention, and running observability only when working on it."],
            ["VRAM too small for the chosen model",
             "Medium",
             "Start at 0.5B in fp16; move to a 4-bit quantisation if a larger model is wanted. Model "
             "size is irrelevant to the DevOps narrative - saying so is itself a good answer."],
            ["Disk exhaustion",
             "Medium",
             "Already hit once. Everything large lives on the working drive; the system drive is "
             "kept clear."],
            ["An accidental cloud charge",
             "Low",
             "A billing alarm set before any Terraform, free-tier services only, no compute of any "
             "kind, and a tested `terraform destroy`."],
            ["**Scope creep** - adding RAG, a service mesh, multi-cloud, an operator",
             "**High**",
             "The exclusion list in section 4.1 is binding. New ideas go to `docs/FUTURE.md`, not "
             "into the repository. **This is the most likely way the project fails.**"],
            ["Built but never written up",
             "Medium",
             "A milestone is not finished until its document exists. That is the definition, not an "
             "aspiration."],
            ["Losing momentum without a schedule",
             "Medium",
             "The counterweight to working without one: every milestone ends in something "
             "demonstrable, so progress is always visible and the project is always presentable as "
             "it stands."],
        ],
        widths=[1.55, 0.75, 4.3],
    )


def verification(D):
    D.h1("7. Acceptance Tests")
    D.p("Each milestone is proven by a command, not by a feeling.")
    D.table(
        ["Milestone", "Verify with", "Expected"],
        [
            ["M0", "`make down && make up && make gpu-check`",
             "`M0 ACCEPTANCE PASSED`; `make doctor` reports 28 passed, 0 failed **(met)**"],
            ["M1", "`curl -N localhost:8080/v1/chat/completions -d '{...}'`",
             "Tokens stream back, generated on the local GPU"],
            ["M2", "`cosign verify ghcr.io/saimcyber/palisade-gateway@sha256:...`",
             "Signature verifies against the GitHub identity; SBOM attached; no AWS secrets stored "
             "in the repository"],
            ["M3", "`argocd app get palisade`, then apply an unsigned image",
             "Synced and Healthy; the unsigned image is **denied by Kyverno**; vLLM has no outbound "
             "network"],
            ["M4", "`k6 run tests/load/two-tenants.js`",
             "Divergent spend per tenant on the dashboard; tenant B receives `429` at its cap while "
             "A is unaffected"],
            ["M5", "`k6 run tests/load/saturation.js`",
             "Meets the targets in `docs/SLO.md`; the public URL responds; all documents present"],
        ],
        widths=[0.7, 2.55, 3.35],
    )
    D.callout("Final acceptance",
              "On a clean machine, `git clone` followed by `make up` reproduces the platform, and "
              "the screenshots in the README match what appears on screen. **If a stranger cannot "
              "reproduce it, it is a demo rather than a platform** - and that difference is exactly "
              "what is being assessed.", "ok")


def cost(D):
    D.h1("8. Cost Control")
    D.table(
        ["Service", "What is used", "Cost"],
        [
            ["Compute / GPU", "The local laptop", "$0"],
            ["Kubernetes", "k3d, running locally in Docker", "$0"],
            ["Container registry", "GitHub Container Registry, public", "$0 - unlimited for public images"],
            ["CI/CD", "GitHub Actions, public repository", "$0 - unlimited minutes for public repos"],
            ["Object storage", "AWS S3, well under the free tier", "$0"],
            ["Identity", "AWS IAM, OIDC provider and roles", "$0 - IAM is always free"],
            ["Image signing", "Sigstore public good instance", "$0"],
            ["Public demo URL", "Cloudflare Tunnel, free plan", "$0"],
            ["**Total**", "", "**$0**"],
        ],
        widths=[1.35, 3.55, 1.7],
    )
    D.callout("Two guard rails",
              "Set a billing alarm before writing a single line of Terraform, and never let "
              "Terraform provision compute - **no EC2, no EKS, no NAT gateway, no load balancer.** "
              "Those four are what generate surprise bills. Storage and identity do not.", "warn")

    D.h2("8.1  The cost model to be able to quote")
    D.p("`docs/COST.md` should answer the question an AI company is genuinely wrestling with: **at "
        "what point does self-hosting beat paying per token?**")
    D.bullet("A hosted API has near-zero fixed cost and a linear per-token price. It wins at low and spiky volume.")
    D.bullet("A self-hosted GPU has a large fixed cost paid whether or not it is busy, and a near-zero marginal cost per token. It wins at high, steady volume.")
    D.bullet("**The break-even is therefore a function of utilisation, not volume alone** - which is precisely why the GPU utilisation dashboard is a financial instrument as much as a technical one.")
    D.bullet("Then the second-order factors that often decide it regardless of the arithmetic: data residency, latency floors, provider rate limits, and vendor concentration risk.")
