# 10. Trivy gate: fail on HIGH/CRITICAL only

- **Status:** Accepted

## Context

Trivy can gate a build on any severity threshold, and can scan either the
Dockerfile/source tree or the image actually built from it. Too strict a
gate blocks merges on findings nobody can act on (a MEDIUM in a base-image
library with no available fix); too loose a gate is decoration, not a
control.

## Decision

Gate on **HIGH and CRITICAL only**, scanning the **built image**, not just
the source tree or Dockerfile.

- This matches the milestone's own acceptance criterion exactly - it names
  a scan gate without specifying MEDIUM, and adding a stricter threshold
  than what was actually agreed isn't a stronger control, it's scope creep
  that risks blocking a merge on something nobody signed up to fix on this
  timeline-free, single-maintainer project.
- Scanning the **built image** (not the Dockerfile or `requirements.txt` in
  isolation) catches what actually ships - a vulnerable library pulled in
  transitively, or something present in the base OS layer, that a
  source-only scan would miss entirely.
- `aquasecurity/trivy-action` is pinned to **v0.35.0 or newer**, not
  whatever tag looks current. `trivy-action`, `setup-trivy`, and the `trivy`
  binary itself were distributed compromised in a real credential-leak
  incident (GitHub Discussion #10425); everything before that fix is
  outside the safe range. A supply-chain-scanning tool getting compromised
  is exactly the failure mode this milestone exists to guard against, so
  the fix floor is treated as a hard requirement, not a suggestion.

## Consequences

- If a real HIGH/CRITICAL finding with no available fix ever blocks a
  merge, the documented path is a reviewed `.trivyignore` entry with a
  reason attached in the PR - not lowering the gate, and not an
  indefinite, unreviewed suppression.
- A MEDIUM or LOW finding can still be seen in the scan output and triaged
  by choice; it just doesn't fail the build on its own.
