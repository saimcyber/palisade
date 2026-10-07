# Architecture

## System overview

```mermaid
flowchart TB
    subgraph internet["Public internet (planned)"]
        caller["API caller"]
    end

    subgraph tunnel["Cloudflare Tunnel"]
        cf["cloudflared"]
    end

    subgraph k8s["k3d cluster (WSL2, RTX 3050)"]
        subgraph palisade_ns["namespace: palisade"]
            ingress["Traefik Ingress"]
            gw["Gateway (FastAPI)\nauth · guard · budget · cache · load-shed"]
            redis["Redis\nrate limits · budgets · cache"]
            vllm["vLLM\nQwen3-0.6B, zero egress"]
            verify["model-verify Job\nSHA-256 + signature check"]
        end

        subgraph monitoring_ns["namespace: monitoring"]
            prom["Prometheus"]
            graf["Grafana\n4 dashboards"]
            ksm["kube-state-metrics"]
            gpuexp["gpu-exporter\n(project-built)"]
        end

        subgraph argocd_ns["namespace: argocd"]
            argocd["Argo CD\napp-of-apps, self-heal"]
            kyverno["Kyverno\nsignature + pod-security policy"]
        end
    end

    subgraph gh["GitHub"]
        repo["palisade repo\n(main branch)"]
        ci["Actions: build → scan → sign → attest"]
        ghcr["GHCR\nsigned images"]
    end

    caller -->|HTTPS| cf -->|localhost only| ingress
    ingress --> gw
    gw --> redis
    gw -->|"X-Request-ID"| vllm
    verify -.->|"signed manifest\ncheck before vLLM starts"| vllm

    prom -->|scrape| gw
    prom -->|scrape| vllm
    prom -->|scrape| ksm
    prom -->|scrape| gpuexp
    prom -->|scrape| kyverno
    graf --> prom

    repo -->|push| ci --> ghcr
    argocd -->|poll| repo
    argocd -->|deploy| palisade_ns
    argocd -->|deploy| monitoring_ns
    kyverno -.->|verify signature\nat admission| palisade_ns
    kyverno -.->|verify signature\nat admission| gpuexp
    ghcr -.->|pull + verify| kyverno
```

## Sync-wave ordering (why things start in this order)

```mermaid
flowchart LR
    w_1["wave -1\npalisade-policies\nKyverno + NetworkPolicies"]
    w0a["wave 0\npalisade-secrets\nSOPS-decrypted tenant config"]
    w1["wave 1\npalisade chart\nPVC → model-verify → vLLM → gateway"]
    w2["wave 2\npalisade-observability-secrets\nGrafana admin password"]
    w3["wave 3\npalisade-observability\nPrometheus, Grafana, exporters"]

    w_1 --> w0a --> w1
    w1 -.->|"never blocks"| w2
    w2 --> w3
```

Policies before secrets before workloads is load-bearing: a pod
admitted before its policy exists is never re-judged until it restarts
(ADR 0020). Observability is deliberately *after* and *decoupled* -
wave 3 depends on wave 1 having succeeded, but nothing in wave 1 ever
waits on wave 3 (ADR 0023). A stalled Grafana image pull must never be
able to block the gateway or vLLM from deploying.

## The request path

```mermaid
sequenceDiagram
    participant C as Caller
    participant G as Gateway
    participant R as Redis
    participant V as vLLM

    C->>G: POST /v1/chat/completions
    G->>R: check rate limit (Lua, atomic)
    alt over limit
        G-->>C: 429 rate_limited
    end
    G->>G: prompt guard (length/injection/PII)
    alt rejected
        G-->>C: 400
    end
    G->>R: reserve budget estimate (Lua, atomic)
    alt over budget
        G-->>C: 429 budget_exhausted
    end
    G->>R: cache lookup (tenant + body hash)
    alt cache hit
        G->>R: bill actual usage to budget
        G-->>C: 200 (cached)
    else cache miss
        G->>G: try acquire in-flight slot
        alt saturated
            G->>R: refund reservation
            G-->>C: 503 upstream_saturated
        else slot acquired
            G->>V: forward request (X-Request-ID)
            V-->>G: response + real usage
            G->>R: reconcile budget (actual - estimate)
            G->>R: store in cache
            G-->>C: 200
        end
    end
    G->>G: emit chat_completion_settled audit line
```

Six independent checks happen before a single GPU cycle is spent, each
cheaper than the one after it - the expensive resource is protected by
a series of progressively more expensive filters, in the order their
actual cost justifies.

## Trust boundaries

| Boundary | What crosses it | What enforces it |
| --- | --- | --- |
| Public internet → Cloudflare Tunnel | HTTPS requests to the gateway only | Cloudflare's own edge TLS; tunnel exposes `/v1/*` exclusively |
| Caller → Gateway | A bearer token (hashed immediately, never retained raw) | `app/auth.py` |
| Gateway → vLLM | An already-policy-rewritten, already-budgeted request | `app/policy.py`, NetworkPolicy (gateway-only ingress to vLLM) |
| vLLM → anywhere | **Nothing** - zero egress, by policy, not by convention | `deploy/policies/networkpolicy-vllm.yaml`, ADR 0014 |
| GitHub Actions → GHCR | A signed, SBOM-attested image | Cosign keyless signing tied to the exact workflow identity |
| GHCR → Cluster | An image Kyverno has independently re-verified | `deploy/policies/kyverno-verify-signatures.yaml` - the registry's own trust is never assumed |
| Git repository → Live cluster | Any change, through Argo CD only | `selfHeal` reverts anything applied by hand |

## Why this shape, not another

See ADR 0011 (one Helm chart, not two), ADR 0012 (model verification as
a separate Job, not an init container - NetworkPolicy is per-pod, and
the verifier needs the internet while vLLM must never have it), ADR
0016 (Argo CD app-of-apps over a single flat manifest set), and ADR
0023 (observability as its own decoupled, lower-priority chain). Each
of these was a real alternative considered and rejected, not the only
option that existed.
