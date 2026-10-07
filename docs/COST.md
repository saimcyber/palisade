# Cost

What this actually costs on real cloud infrastructure, and the
self-host-versus-hosted-API break-even, worked from measured numbers
and current prices - not list prices quoted from memory.

## This project's own cost: $0

Everything in Palisade runs on hardware already owned (a laptop with an
RTX 3050) and free-tier cloud services (GitHub Actions, GHCR, the OIDC-
federated AWS access that provisions nothing billable - ADR 0009). No
cloud compute is ever provisioned. This section exists to answer "what
would this cost if it had to run on rented infrastructure," not to
report a real bill.

## What a GPU to run this actually costs, rented

| Instance | GPU | On-demand, hourly | Source |
| --- | --- | --- | --- |
| AWS `g5.xlarge` | 1x A10G, 24 GB VRAM | **$1.006/hr** (~$734/month if left running continuously) | [Holori AWS pricing calculator](https://calculator.holori.com/aws/ec2/g5.xlarge/us-east-1) |

A `g5.xlarge` is the realistic floor for serving a model this size with
real headroom - it has 6x this project's own VRAM. The RTX 3050's 4 GB
is why Palisade runs a 0.6B model at all (CLAUDE.md's machine
constraints); a cloud deployment of the same architecture would still
want a GPU with meaningfully more VRAM than the exact minimum, for the
same KV-cache-sizing reasons ADR 0002 and the M1 spike ran into
repeatedly on this hardware.

## Measured throughput, this hardware

From the real saturation run against the actual RTX 3050
(`docs/evidence/m5/01-saturation-real-gpu.txt`): 22 requests actually
served under load, each a 16-token completion, over a 45-second window
in which the gateway was simultaneously shedding and rate-limiting the
rest of a 30-VU flood. That's **≈352 completion tokens generated in
45s ≈ 7.8 tokens/sec, aggregate, under contention** - a conservative
figure, not a clean best-case number, since it includes connection
overhead and the gateway's own per-request work (budget reservation,
cache lookup) competing for the same CPU as everything else running on
this laptop. A dedicated, uncontended measurement is listed as an open
item in `docs/SLO.md` and would very likely show a higher ceiling.

## Hosted-API comparison

| Provider / model | Price per 1M tokens (in / out) | Source |
| --- | --- | --- |
| OpenAI `gpt-4o-mini` | $0.15 / $0.60 | [pricepertoken.com](https://pricepertoken.com/pricing-page/model/openai-gpt-4o-mini) |

`gpt-4o-mini` is the fairest hosted comparison available - a small,
cheap, general-purpose model, the same tier Palisade's own 0.6B model
occupies, rather than comparing against a frontier model nobody would
actually pick for this workload.

## The break-even

Cost per output token is the fair comparison, not cost per hour -
rental is time-priced, the hosted API is token-priced, so the only
honest way to compare them is to convert both to the same unit.

- **Self-hosted, measured**: $1.006/hr ÷ (7.8 tokens/sec × 3,600) ≈
  $1.006 ÷ 28,080 tokens ≈ **$35.82 per 1M output tokens**.
- **Hosted (`gpt-4o-mini`)**: **$0.60 per 1M output tokens**.

**At this measured, contended throughput, self-hosting this model costs
roughly 60x more per token than the hosted API** - not a close call,
and not the direction a first guess might expect.

**The honest conclusion:** self-hosting a model this small does not
beat a hosted API on raw cost, at this measured throughput, by a wide
margin. The case for self-hosting here was never the price per token -
it's everything this project actually built around the model: per-
tenant budgets enforced before the GPU is touched, a verified supply
chain, policy enforcement at admission, zero egress from the model
server, and full visibility into exactly what's running and why. A
hosted API gives none of that by default; what it does give, at this
project's measured throughput, is a dramatically cheaper token. The
60x gap is itself bounded by this specific hardware's VRAM ceiling
(ADR 0002) and the measured run's heavy contention, not by anything
fundamental to self-hosting as a strategy - a properly provisioned,
uncontended GPU serving a larger model to real concurrent traffic is a
genuinely different cost equation, just not the one this laptop can
measure.

## What would change the answer

- **A larger self-hosted model, properly provisioned** (not VRAM-
  starved) closes the gap - `gpt-4o-mini`-class hosted pricing assumes
  the provider's own batching efficiency at scale, which a single-
  tenant, single-GPU deployment can't match per-token, but a
  multi-tenant deployment on rented hardware serving many customers
  concurrently could.
- **Sustained, high-utilisation traffic** changes the comparison -
  this project's own measured throughput is a worst case (contended,
  short burst), not a steady-state ceiling.
- **Data residency, compliance, or latency requirements** that a hosted
  API can't meet make this comparison moot in either direction - cost
  isn't always the deciding constraint.
