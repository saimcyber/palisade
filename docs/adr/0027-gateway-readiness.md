# 27. Gateway readiness reflects the gateway, not its shared dependencies

- **Status:** Accepted. Supersedes in part ADR 0021's note on `/readyz`.

## Context

Since M1 the gateway's readiness probe was `/readyz`, which returns `503`
unless both vLLM and Redis answer. The intent was sound - "don't send
traffic to a gateway that can't serve it" - and ADR 0021 leaned on it as
the way a lost Redis stops requests being served without budget checks.

`make demo`'s chaos step showed what it actually did. While vLLM
restarted, the single gateway pod failed `/readyz`, was removed from its
Service, and:

- callers got Traefik's `503 no available server` - an answer the gateway
  never saw, so no audit line and no metric;
- Prometheus, which scrapes the gateway through that same Service, lost
  the target: `up{job="palisade-gateway"}` read `0` for the whole outage
  and every gateway series went stale, exactly when they were needed;
- `PalisadeSLOBurnRateHigh`, built on the gateway's own request counter,
  could not see a complete outage at all.

Gating readiness on a dependency only helps when some replicas can reach
it and others can't, so traffic can move to the healthy ones. Every
gateway replica shares one vLLM and one Redis: when either is down, they
are all down together, and readiness gating removes every replica at once.
It protects nothing; it only moves the failure somewhere it can't be
observed.

## Decision

**The kubelet probes `/healthz` (process alive) for readiness. `/readyz`
stays, as an operator's dependency check.**

The gateway already fails closed per request when a dependency is down,
which is what actually enforces safety:

- vLLM unreachable: `UpstreamError` - an audited `503 "Upstream model
  server unreachable"`, counted in `palisade_http_requests_total`;
- Redis unreachable: every Redis call sits behind the handler's
  `RedisError` catch - an audited `503 redis_unavailable`, never a request
  served with its rate limit or budget unchecked (chaos experiment 2's fix).

The SLO alert was corrected alongside, because it now sees these failures:
it subtracts deliberate load-shed `503`s (ADR 0024) so that shedding - the
system working as designed - doesn't page, while a dependency outage does.
`docs/SLO.md` already said the two were kept apart in alerts; the rule
did not actually do it until now.

## Rejected

- **Keep `/readyz` as the probe and scrape pods directly** (a headless
  Service with `publishNotReadyAddresses`): fixes the missing metrics, but
  callers still get the ingress's anonymous `503`, uncounted, so the SLO
  alert stays blind.
- **Measure availability at the ingress instead** (Traefik's own metrics):
  the more standard place for an availability SLI, and worth doing in a
  larger deployment - but it would leave the gateway's audit log silent
  during an outage, and the audit log is this platform's record of what
  happened to each tenant's requests.

## Consequences

- During a dependency outage the gateway keeps receiving traffic and
  answers each request quickly and identifiably, instead of the ingress
  answering for it.
- A replica that is genuinely broken in itself (hung event loop, crashed
  worker) still fails `/healthz` and leaves rotation; liveness unchanged.
- If this platform ever runs gateway replicas against *different*
  backends (per-zone vLLM, say), dependency-aware readiness becomes useful
  again, and this decision should be revisited for that topology.
- Evidence: `make demo` §8 asserts the gateway's own `503` during the vLLM
  kill; §9 asserts Prometheus kept the gateway target `up` throughout.
