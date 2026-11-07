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
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54

# Debian security updates applied at build time, not left to whenever the
# upstream base is next republished: a base digest can lag a published fix
# by days (seen: zlib CVE-2026-76844/85091 fixed in deb13u1, base still on
# +b1). The resulting image is still pinned by digest, and its SBOM records
# the exact package versions that went in.
RUN apt-get update && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL https://github.com/getsops/sops/releases/download/v3.13.3/sops-v3.13.3.linux.amd64 -o /usr/local/bin/sops \
    && chmod 0755 /usr/local/bin/sops \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
