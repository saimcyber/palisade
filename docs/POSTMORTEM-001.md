# Postmortem 001: silent audit-log corruption on upstream failure

Blameless by design - the goal is the mechanism, not who wrote the
original code. Both bugs below existed from the moment the features
they touch were first merged; neither was a regression from a recent
change. They surfaced the first time this project deliberately went
looking for them.

## Summary

Two independent exception-handling gaps in the gateway's request path
meant that when either vLLM or Redis failed mid-request, the gateway's
own audit log - the thing this platform exists to make trustworthy -
recorded the wrong outcome, or no outcome at all. A request that
genuinely failed could be logged as `outcome: "ok", status: 200`. A
request that failed because Redis was unreachable produced a bare
`500 Internal Server Error` with zero audit trail - not a wrong
record, no record. Both were found by deliberately breaking the
system (chaos-day experiments 1 and 2, `docs/evidence/m5/02-*` and
`03-*`), not by a user report or a monitoring alert, because the
failure mode was specifically one that monitoring could not have
caught: the system believed itself to be healthy.

## Impact

No real tenant traffic was affected - this project has no production
users. Framed as if it did: any request that happened to lose its
connection to vLLM mid-stream would have been billed and logged as a
successful completion, and any request that hit Redis during an outage
would have returned a generic error to the client with nothing in the
audit log to explain why, correlate it with other failures, or even
prove it happened. For a platform whose stated purpose is auditable
per-tenant usage, both are the specific failure mode that defeats the
point of having an audit log at all.

## Timeline

No calendar timestamps are recorded here, consistent with this
project's standing no-time-references rule - the sequence, not the
clock, is what matters.

1. M5's chaos-day plan was written, with hypotheses for five
   experiments recorded before any were run
   (`docs/evidence/m5/chaos-hypotheses.md`).
2. Experiment 1: a streaming request was started, then the vLLM pod
   was deleted mid-generation. The client's stream truncated silently
   (`curl` exited `0`). The gateway's own traceback showed
   `httpx.RemoteProtocolError` propagating past `relay()`'s
   `except UpstreamError` clause - the wrong exception type was being
   caught, so the generic `finally` block ran but never corrected
   `status_code` from its default of `"200"`.
3. Experiment 2: `redis-cli CLIENT PAUSE ALL` was used to stall Redis.
   The very first Redis call in the request path
   (`TenantStore.check_rate_limit`) raised `redis.exceptions.
   TimeoutError` once the pause outlasted the redis client's own ~5s
   socket timeout. Nothing in `create_chat_completion` caught it -
   Starlette's own generic exception handler returned a bare `500`
   with no audit line at all.
4. Both were fixed, tested, and verified live against the real
   cluster before being considered closed (see "Fixes" below).

## Root cause

Both bugs share one root cause: the request handler's error handling
was built incrementally, one upstream dependency at a time, and each
addition only covered the failure modes that had actually been
observed by then (`httpx.ConnectError`, `httpx.TimeoutException`,
`httpx.HTTPStatusError`). Neither `httpx.RemoteProtocolError` (a
mid-stream disconnect, distinct from a connect-time failure) nor any
`redis.exceptions.RedisError` subtype had ever been observed before
chaos day, because nothing had previously forced either dependency to
fail mid-request. The code was correct for every failure mode anyone
had thought to test, and silently wrong for the two nobody had.

This is not a one-off coding mistake so much as a structural one: an
`except SpecificException` clause is a bet that you have correctly
enumerated every way the thing underneath can fail. Chaos day exists
specifically to find out where that bet is wrong, under controlled
conditions, before an untested failure mode finds you some other way.

## Detection

Neither bug was caught by any existing alert, test, or review -
confirmed by re-checking: `PalisadeSLOBurnRateHigh` tracks `5xx` rate,
and bug #1's symptom was a false `200`, invisible to it; bug #2
produced a real `500`, which that alert *would* have caught, but only
after the fact and with no indication from the audit log of which
tenant or request was affected beyond what Starlette's generic handler
happened to log. Both were found exclusively by chaos day's
deliberate-failure methodology: write the hypothesis, break the real
dependency, read what actually happened. This is itself the argument
for chaos testing as a practice, not a one-time M5 checkbox - these
two gaps had existed since the features they're part of were first
written, and would not have been found any other way short of an
actual incident.

## Fixes

**Bug #1** (`services/gateway/app/upstream.py`): `stream_chat_completion`
now catches `httpx.RemoteProtocolError` explicitly and raises it as an
`UpstreamError(502, ...)`, so `relay()`'s existing error path runs
correctly. Regression test:
`tests/test_streaming.py::test_upstream_disconnecting_mid_stream_is_a_handled_upstream_error`.
Verified live post-deploy: an identical mid-stream kill now produces
`outcome: "upstream_error", status: 502` in the audit log
(`docs/evidence/m5/02-*`).

**Bug #2** (`services/gateway/app/routes/chat.py`): the route handler
is now a thin wrapper around the original logic, catching
`redis.exceptions.RedisError` and returning a clean, audited `503`
(`outcome: "redis_unavailable"`) instead of letting Starlette's
generic handler take it. The streaming path's post-stream
reconciliation gets its own narrower catch, since by that point a
status code can no longer be changed. Regression tests:
`tests/test_redis_unavailable.py`. Verified live post-deploy: an
identical Redis pause now produces `{"error": "redis_unavailable"}`
at `HTTP 503` instead of a bare `500` (`docs/evidence/m5/03-*`).

## What chaos day also found, beyond these two bugs

Not every chaos-day finding was a bug. Recorded here because a
postmortem that only lists failures teaches the wrong lesson about
what the exercise is for:

- **Redis data survives more restarts than documented** - a container
  restarting in place within the same Pod reloads a pre-existing
  `dump.rdb` from the surviving `emptyDir`, so tenant budgets do not
  reset on every Redis restart as ADR 0023's original wording implied
  - only on a genuine Pod reschedule. Corrected in
  `redis-deployment.yaml`'s header and M4's limitations table
  (`docs/evidence/m5/04-*`).
- **Kyverno's signature policy is identity-exact in both directions**
  - a real signature from the wrong GitHub Actions workflow is refused
  exactly like no signature at all, and an old but genuinely
  `ci.yml`-signed digest is admitted regardless of age
  (`docs/evidence/m5/05-*`, `06-*`).
- **VRAM exhaustion degrades soft on this host, not hard** - a finding
  about this machine's WSL2/WDDM driver stack, not about the
  application. See `docs/evidence/m5/07-*` for the full mechanism
  (the Windows driver pages idle GPU allocations out to host RAM
  instead of returning an out-of-memory error) and the explicit caveat
  that this would very likely fail hard on a native Linux host. A
  genuine observability gap surfaced alongside it: no alert exists for
  GPU *memory* pressure, only GPU compute utilization
  (`PalisadeGPUSaturated`), even though the test's own Prometheus data
  showed memory pressure peaking at ~95.4% of the card.

## Action items

| Action | Status |
| --- | --- |
| Catch `httpx.RemoteProtocolError` in the streaming path | Done |
| Catch `redis.exceptions.RedisError` around the request handler | Done |
| Correct ADR 0023 / `redis-deployment.yaml`'s restart-reset claim | Done |
| Add a GPU memory-pressure alert (found during experiment 5, not yet acted on) | Not done - documented as a known gap |
| Re-run the VRAM exhaustion experiment on a native Linux host, if one becomes available, to confirm the hard-OOM prediction | Not done - no such host available to this project |

## Lessons learned

The specific lesson is narrow: an exception handler that only covers
observed failure modes is a liability disguised as a feature, because
it looks complete. The broader one is what justified M5's chaos day
existing at all - the two most damaging bugs in this entire project
were not caught by any test, alert, or code review, because nothing
had ever actually broken the dependencies they depend on. Both were
found in the time it took to write a `kubectl delete pod` and a
`redis-cli CLIENT PAUSE` command. The actual lesson is not "write
chaos tests" as a one-time M5 deliverable - it's that an audit-logging
system's correctness claims are only as strong as the failure modes
someone has actually gone looking for, and this project's own
dependencies (vLLM, Redis) still have failure modes nobody has tested
yet.
