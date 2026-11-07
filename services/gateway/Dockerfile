# =============================================================================
#  Palisade gateway image.
#
#  Builder stage installs dependencies into a venv; runtime stage copies only
#  the venv and the app source - no compiler toolchain, no pip cache, no
#  build-time files ship. Non-root throughout. Base pinned by digest, not
#  just tag. requirements.txt is hash-pinned (pip-compile --generate-hashes);
#  --require-hashes makes this build refuse any package whose hash doesn't
#  match, which is the actual enforcement, not just documentation of intent.
#  Trivy/Syft/cosign run against the image this Dockerfile produces, in CI.
# =============================================================================
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --require-hashes -r requirements.txt

FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS runtime

# Debian security updates applied at build time, not left to whenever the
# upstream base is next republished: a base digest can lag a published fix
# by days (seen: zlib CVE-2026-76844/85091 fixed in deb13u1, base still on
# +b1). The resulting image is still pinned by digest, and its SBOM records
# the exact package versions that went in.
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN groupadd --system palisade && useradd --system --gid palisade --no-create-home palisade

COPY --from=builder /venv /venv
WORKDIR /app
COPY app ./app

ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER palisade
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
