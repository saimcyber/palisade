# 26. The public demo is an operator-run Cloudflare Quick Tunnel in front of the Ingress - off by default, never part of the platform

- **Status:** Accepted

## Context

The plan calls for "a Cloudflare Tunnel demo, protected by a demo tenant
with a hard budget cap" - a URL a reviewer can actually `curl`, without
this laptop opening an inbound port, owning a domain, or paying for
anything. Three things had to be decided: which kind of tunnel, where it
runs, and what exactly it exposes.

## Decision

**A Cloudflare Quick Tunnel, started by a person with `make tunnel`, run
on the host (not in the cluster), pointed at the real Traefik Ingress -
whose routes were narrowed to an explicit allowlist first.**

- **Quick Tunnel, not a named tunnel.** A named tunnel needs a Cloudflare
  account, a domain on Cloudflare, and a long-lived tunnel credential that
  would then have to be stored, rotated and kept out of git. A Quick Tunnel
  needs none of that: no account, no token, and a new random
  `*.trycloudflare.com` hostname every start. Nothing to leak, nothing to
  revoke. For a demo that only needs to exist while someone is looking at
  it, that is the property that matters most.
- **Host-run and opt-in, not an in-cluster Deployment.** An in-cluster
  `cloudflared` Deployment would be the GitOps-native choice for a
  permanent tunnel. Here it would make "this cluster is on the public
  internet" part of desired state: on whenever the cluster runs, re-created
  by Argo CD's self-heal if someone deleted it, and dependent on an
  unauthenticated third-party endpoint at every sync. Public exposure
  should be a deliberate action someone takes and can see, so it is a
  script with `up`/`status`/`down`, and it is down unless an operator says
  otherwise.
- **Through the Ingress, not straight at the gateway Service.** Pointing
  `cloudflared` at `localhost:8080` with `Host: palisade.local` means the
  public path is the same path every other client takes, through the same
  routing rules. That made the Ingress's routing the security boundary -
  and it turned out not to be one yet. It routed `/`, which exposed
  `/metrics` (every tenant's name, spend and remaining budget), `/docs`,
  `/openapi.json` and `/readyz`. It was narrowed to `/v1` (Prefix) and
  `/healthz` (Exact) before the tunnel ever ran; Prometheus scrapes the
  Service directly and was unaffected.
- **The capped demo tenant.** `tenant-public` (10 requests/minute, 3000
  tokens per budget window) is the only key ever handed out for the
  tunnel. Its rate limit and budget are enforced by the gateway, in Redis,
  before the GPU is touched - the same mechanism M4 proved for tenant-b.

## Rejected

- **A named tunnel or `ngrok`**: an account and a credential to manage,
  for no benefit a short-lived demo needs.
- **Opening a port / port-forwarding a home router**: exposes the host
  itself, needs a stable address, and has no TLS without more work.
- **Exposing Grafana or Prometheus too**: dashboards are for the operator.
  A reviewer gets screenshots in the README; the live dashboards stay on
  `make dashboards`, localhost only.

## Consequences

- The tunnel does not restrict *which* tenant authenticates through it -
  any valid key works, exactly as through the local Ingress. "Only
  tenant-public's key is shared" is an operating procedure, not an
  enforced control. Making it enforced would need an edge rule
  (Cloudflare Access, or a Traefik middleware keyed on the tunnel's
  traffic), which an account-less Quick Tunnel cannot carry.
- Quick Tunnels have no uptime guarantee, and provisioning one can exceed
  cloudflared's own 15s request timeout - seen live. `scripts/tunnel.sh`
  retries at most three times, then fails clearly rather than hanging.
- The URL changes every start, so it never appears in the README. The
  README documents how to start one instead.
- Evidence: `docs/evidence/m5/10-public-tunnel.txt` - the allowlist,
  auth, a completion, incremental streaming and the rate limit, all
  exercised from the public side.
