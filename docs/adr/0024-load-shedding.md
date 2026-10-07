# 24. Load shedding: a plain in-process counter, not a queue

- **Status:** Accepted

## Context

The project plan names "deliberate load shedding" explicitly (§2.3, step
8: "If its queue is saturated, the gateway sheds load cleanly rather
than letting everything time out") and the risk table calls for "a
bounded queue, admission control by token budget, and graceful load
shedding" as what a real platform does under GPU scarcity. Through M4,
nothing in the gateway implemented this - a request past its budget and
rate-limit checks went straight to vLLM regardless of how many other
requests were already waiting on it, which on a single-replica, no-
autoscaling model tier (ADR 0005) means unbounded queueing, not
shedding.

## Decision

`loadshed.py`'s `InFlightLimiter` is a plain integer counter with
`try_acquire`/`release`, not `asyncio.Semaphore`, a queue, or anything
Redis-backed. Three reasons, in order of how much they mattered:

1. **This is about one process's own capacity, not a cross-replica
   resource.** There is exactly one gateway replica and exactly one vLLM
   replica (ADR 0005) - Redis-shared state would add a network round
   trip to answer a question only this process's own memory needs to
   answer.
2. **Load shedding has to be synchronous and immediate.** `try_acquire()`
   returns `bool` with no `await` - a request that can't get a slot is
   rejected in the same tick, not after waiting on a semaphore that would
   eventually grant it (which is queueing with a delay, not shedding).
3. **No lock is needed.** This process is single-threaded cooperative
   asyncio; a check-then-increment with no `await` between the two
   statements cannot be interrupted by another coroutine, so the
   counter is already race-free.

Wired into `chat.py` at the one place that matters: immediately before
the call to vLLM, on both the streaming and non-streaming paths, after
every cheaper check (rate limit, prompt guard, budget) has already
passed. A shed request gets `503` with `Retry-After: 2` and a
labelled metric (`palisade_load_shed_total`); its budget reservation is
refunded, since no tokens were ever generated for it.

## Consequences

- `max_in_flight_upstream_requests` (default 8) is a guess tuned against
  nothing yet - M5's saturation load test is what actually calibrates it
  (`docs/SLO.md`).
- A cache hit never touches this limiter - it doesn't reach vLLM, so it
  has no reason to compete for the slot a real generation needs.
- This bounds *this gateway's* concurrency, not vLLM's own internal batch
  size - vLLM still batches whatever gets through. The two numbers are
  related but not the same knob, and conflating them was a mistake worth
  naming here so a future milestone doesn't repeat it.
- If the gateway ever runs more than one replica, this limiter stops
  being correct (each replica would allow its own 8, for a combined 16
  against one vLLM) - the Redis-backed design this ADR rejected for M4
  would become the right one then, not before.
