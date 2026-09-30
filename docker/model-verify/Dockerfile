# =============================================================================
#  Model-verification init container.
#
#  Runs before vLLM's own container starts (Kubernetes runs initContainers
#  in order and only proceeds once each exits 0). Refuses to let the main
#  container start if the model weights on the shared cache volume don't
#  match a manifest this project committed and signed itself.
#
#  Build context is the REPO ROOT, not this directory - the image bakes in
#  deploy/model-manifests/*.json (+.sigstore.json) so the thing being
#  verified against ships immutably with the verifier, not fetched at
#  runtime from a source that could itself be tampered with.
#
#    docker build -f docker/model-verify/Dockerfile .
# =============================================================================
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS builder

WORKDIR /build
COPY docker/model-verify/requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --require-hashes -r requirements.txt

FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS runtime

RUN groupadd --system verify && useradd --system --gid verify --no-create-home verify

# cosign, pinned - verifies the manifest's signature before anything in it
# is trusted. Same version scripts/install-tools.sh pins on the host.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64 -o /usr/local/bin/cosign \
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
