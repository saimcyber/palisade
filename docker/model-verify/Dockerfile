# =============================================================================
#  Model-verification Job image.
#
#  Runs as its own Argo CD Sync-hook Job (deploy/charts/palisade/templates/
#  model-verify-job.yaml), ordered by sync-wave to complete before vLLM's
#  own Deployment is ever applied - not a vLLM initContainer, because
#  NetworkPolicy can't grant this container egress while denying it to
#  vLLM's in the same pod (ADR 0012, 0014). Refuses to exit 0 if the model
#  weights on the shared cache volume don't match a manifest this project
#  committed and signed itself.
#
#  Build context is the REPO ROOT, not this directory - the image bakes in
#  deploy/model-manifests/*.json (+.sigstore.json) so the thing being
#  verified against ships immutably with the verifier, not fetched at
#  runtime from a source that could itself be tampered with.
#
#    docker build -f docker/model-verify/Dockerfile .
# =============================================================================
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS builder

WORKDIR /build
COPY docker/model-verify/requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --require-hashes -r requirements.txt

FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS runtime

RUN groupadd --system verify && useradd --system --gid verify --no-create-home verify

# cosign, pinned - verifies the manifest's signature before anything in it
# is trusted. Same version scripts/install-tools.sh pins on the host.
# Debian security updates applied at build time, not left to whenever the
# upstream base is next republished: a base digest can lag a published fix
# by days (seen: zlib CVE-2026-76844/85091 fixed in deb13u1, base still on
# +b1). The resulting image is still pinned by digest, and its SBOM records
# the exact package versions that went in.
RUN apt-get update && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL https://github.com/sigstore/cosign/releases/download/v3.1.4/cosign-linux-amd64 -o /usr/local/bin/cosign \
    && chmod 0755 /usr/local/bin/cosign \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
WORKDIR /app
COPY docker/model-verify/verify.py .
COPY deploy/model-manifests/ ./manifests/

ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER verify
ENTRYPOINT ["python", "/app/verify.py"]
