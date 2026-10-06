# 21. Tenant store split: static facts in config, mutable state in Redis

- **Status:** Accepted

## Context

M4's acceptance test needs per-tenant rate limits, per-tenant token
budgets, and a per-tenant response cache - and the budget check has to be
race-safe under concurrent requests from the same tenant, which the
single-process, in-memory `api_key_hashes` set from M1 cannot provide once
the gateway runs more than one replica.

auth.py's own comment since M1 said "M4 moves the lookup to Redis" -
meaning everything about a tenant. Implementing that literally would need
a seeding mechanism (something has to write tenant records into Redis
before the gateway can authenticate anyone) and would make "what tenants
exist and what are their limits" a runtime fact with no record in Git,
which cuts against this project's GitOps posture (docs/adr/0016): the
cluster's behaviour should be reconstructable by reading the repository,
not by inspecting whatever happens to be in Redis right now.

## Decision

Split tenant data by how often it actually changes:

- **Static facts** - name, rate limit, token budget, and which API key hash
  maps to which tenant - live in `PALISADE_TENANTS`, a JSON object sourced
  from a SOPS-encrypted secret (the `TENANTS` key in
  `deploy/secrets/gateway-secret.enc.yaml`), loaded
  once at gateway startup into `app.state.tenants`. Revoking or
  reprovisioning a tenant is a Git commit, consistent with every other
  change to this platform.
- **Mutable state** - requests this rate-limit window, tokens consumed in
  the current budget window, and cached responses - lives in Redis,
  reached via `tenancy.TenantStore` and `cache.ResponseCache`. This is
  exactly the state that must survive a gateway restart and be shared
  across replicas, and the only state for which "what's actually in Redis
  right now" is the correct source of truth.

Both the budget reservation and the rate-limit check are single Lua
scripts (`tenancy.py`), not a read-then-write from Python: two concurrent
requests from the same tenant must not both observe "under budget" before
either commits, which a plain `GET`-then-`SET` cannot guarantee.

Token budgets are a rolling window (`budget_window_seconds`, a Redis TTL),
not a lifetime cap - a real operator wants "N tokens per day", not "N
tokens ever, forever". Window length is runtime behaviour, which the
project's no-time-references rule explicitly exempts.

A cache hit still bills the tenant's budget for the response's *actual*
recorded usage, not zero and not a fresh estimate - skipping this would let
a tenant hide real spend behind a cache hit, which would make the
cost-attribution dashboard this exists to feed actively misleading.

## Consequences

- This is a deliberate deviation from the literal reading of M1's own
  auth.py comment ("M4 moves the lookup to Redis") - recorded here rather
  than smoothed over. A fully Redis-resident tenant store remains possible
  later (an operator-facing issue/revoke API, say); nothing here forecloses
  it, since `auth.py` only depends on `app.state.tenants` being a mapping.
- A tenant revoked by editing `PALISADE_TENANTS` and redeploying takes
  effect on the next pod restart, not instantly - an acceptable latency for
  a portfolio-scale platform, and one Argo CD's own rollout already governs.
- Losing Redis loses rate-limit and budget state (not tenant identity) -
  `/readyz` checks Redis reachability for exactly this reason, so a lost
  Redis takes the gateway out of rotation rather than silently serving with
  no budget enforcement.
