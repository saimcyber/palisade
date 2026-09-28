# 7. Container registry: GitHub Container Registry over Docker Hub

- **Status:** Accepted

## Context

The gateway image needs somewhere to live once CI builds it - somewhere a
signature can be attached to, an SBOM attested against, and a digest pulled
from by anyone verifying the milestone's acceptance criterion.

## Decision

Push to `ghcr.io`, not Docker Hub or another registry.

- **Authentication is free.** A GHCR push from GitHub Actions authenticates
  with the workflow's own built-in `GITHUB_TOKEN` (`packages: write`
  permission) - no separate registry account, no API token to generate,
  store as a repo secret, or rotate. Docker Hub would need its own PAT held
  as a GitHub secret - one more long-lived credential in exactly the kind of
  place this milestone is trying to eliminate them from.
- **Free for a public repository**, with no pull-rate limits to design
  around, unlike Docker Hub's anonymous-pull throttling.
- **Same-platform provenance.** A viewer can trace an image on `ghcr.io/
  saimcyber/palisade-gateway` straight back to the exact repository and
  workflow run that built it, which is also exactly what `cosign verify`'s
  `--certificate-identity` checks against.

## Consequences

- The image's visibility defaults to private on first push and has to be
  made public once, by hand, in GitHub's package settings - a deliberate,
  irreversible step (GitHub does not allow reverting a package back to
  private), not a rubber-stamp default.
- Anyone reviewing this project can verify the signed image without an
  account on any registry - `cosign verify` and `docker pull` both work
  anonymously once the package is public.
