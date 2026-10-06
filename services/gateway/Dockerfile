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
FROM python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --require-hashes -r requirements.txt

FROM python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS runtime

RUN groupadd --system palisade && useradd --system --gid palisade --no-create-home palisade

COPY --from=builder /venv /venv
WORKDIR /app
COPY app ./app

ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER palisade
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
