# 1. Record architecture decisions

- **Status:** Accepted

## Context

Palisade exists to demonstrate engineering judgement, not only working
infrastructure. The reasoning behind a choice is the part an interviewer
probes, and it is exactly the part that is lost if it lives only in my head.

## Decision

Every non-obvious technical choice gets a short ADR in `docs/adr/`, using this
format: Context, Decision, Consequences. One page maximum. Decisions to
*exclude* something are recorded too - knowing what not to build is a
deliberate part of this project.

## Consequences

- A reviewer can reconstruct my reasoning without asking me.
- "Why didn't you use X?" has a written answer rather than an improvised one.
- Small ongoing cost: an ADR must be written at the moment of the decision,
  while the alternatives are still fresh.
