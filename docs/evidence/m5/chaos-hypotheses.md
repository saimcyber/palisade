# Chaos day - hypotheses, written before running anything

Per CLAUDE.md's own working convention and the project's established
pattern: write the hypothesis down, then run the experiment, then
record what actually happened - never adjust the hypothesis after
seeing the result.

## 1. Kill vLLM mid-stream

**Action:** Start a streaming request, then `kubectl delete pod` the
vLLM pod while it's still generating.

**Hypothesis:** The in-flight stream breaks (client sees a truncated
response or a connection error). The gateway's `relay()` `finally`
block still runs - the budget reservation is kept, not refunded
(chat.py's documented choice: "the upstream may have already generated
tokens we have no count for"). A new vLLM pod starts; the Deployment
recovers without intervention. `PalisadeRestartLoop` does **not** fire
from a single kill (threshold is >3 in 15 minutes).

## 2. Hang Redis (`CLIENT PAUSE`)

**Action:** `redis-cli CLIENT PAUSE <ms> ALL` inside the Redis pod -
freezes all client commands for a window without killing the
connection.

**Hypothesis:** In-flight requests that are mid-Lua-script (rate
limit/budget check) hang until the pause lifts or the gateway's own
Redis client times out. `/readyz` may start failing if the pause
outlasts whatever timeout the redis client uses, taking the gateway out
of rotation. No data loss - this is a stall, not a crash.

## 3. Lose Redis (`SHUTDOWN NOSAVE`)

**Action:** `redis-cli SHUTDOWN NOSAVE` - kills the Redis process
immediately, no save, from inside the pod.

**Hypothesis:** The gateway's `/readyz` starts returning 503
immediately (it checks Redis reachability explicitly). In-flight
requests at the Lua-script stage fail with a connection error -
caught by `UpstreamError`'s sibling handling or an uncaught exception
(worth finding out which). Kubernetes restarts the Redis container
(no Deployment-level restart needed, same pod). **Because Redis has no
PersistentVolumeClaim (a documented ADR 0023 trade-off), every tenant's
rate-limit window and budget counter resets to zero on restart** - a
tenant that had exhausted its budget gets a fresh one. This is the
expected, already-documented consequence, not a surprise - the
interesting part is confirming it's exactly this and nothing worse.

## 4a. Bad deploy: wrong-identity signature

**Action:** Apply a Pod spec referencing a digest that *is* validly
signed, but by `model-verify-image.yml`'s identity rather than
`ci.yml`'s - into the gateway's own namespace/selector path.

**Hypothesis:** Kyverno denies it. The policy's `keyless.subject`
match is exact-string on the workflow path; a correctly-signed-but-
wrong-identity image fails verification exactly like an unsigned one,
with a similarly readable reason.

## 4b. Bad deploy: old valid M3 digest

**Action:** Roll the gateway Deployment back to an old, genuinely
CI-signed digest from before the M4 feature set (budgets, cache, load
shedding didn't exist in that build).

**Hypothesis:** Kyverno **admits** it - the signature is real and
correctly identified. The pod starts. Whether it then behaves
correctly is a separate question from whether it's *allowed to run* -
expecting it to start successfully but potentially answer requests
without the newer features (no load shedding, no cache) rather than
fail outright, since nothing about an older API surface should itself
crash the process.

## 5. VRAM exhaustion

**Action:** Force vLLM to request more VRAM than the card has (lower
`--kv-cache-memory-bytes` protection by forcing a concurrent competing
allocation, or raise `--gpu-memory-utilization` past what's actually
free).

**Hypothesis:** Per CLAUDE.md's own prior finding, this fails as
`torch.OutOfMemoryError` at KV-cache allocation, not a clean error the
gateway can route around - the vLLM pod likely crash-loops.
**Accepted risk, approved in advance:** recovery may need a Docker
Desktop restart or a host-level GPU reset, per the machine's documented
WSL2/CDI fragility - this is why it runs last, after every other
experiment's evidence is already safely recorded.
