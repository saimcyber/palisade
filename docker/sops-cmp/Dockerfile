# =============================================================================
#  sops CMP sidecar for Argo CD's repo-server.
#
#  Just sops plus a shell - Argo CD's own entrypoint
#  (/var/run/argocd/argocd-cmp-server) is supplied at the Kubernetes
#  container level (repoServer.extraContainers.command in
#  infra/terraform/cluster/argocd-values.yaml), shared in from the main
#  repo-server container via the var-files volume, not baked into this
#  image - this image only needs to be able to exec it once mounted.
#
#  No third-party sops container image is used here (found no verifiable
#  official one - github.com/getsops/sops ships no Dockerfile in its repo,
#  and an image referenced in early drafts of this file, alpine/sops,
#  turned out not to exist at all on Docker Hub, checked and confirmed
#  404). Built from the same pinned base this project already vets
#  elsewhere instead.
# =============================================================================
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL https://github.com/getsops/sops/releases/download/v3.13.3/sops-v3.13.3.linux.amd64 -o /usr/local/bin/sops \
    && chmod 0755 /usr/local/bin/sops \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
