# =============================================================================
#  Palisade gateway image.
#
#  Builder stage installs dependencies into a venv; runtime stage copies only
#  the venv and the app source - no compiler toolchain, no pip cache, no
#  build-time files ship. Non-root throughout. Base pinned by digest, not
#  just tag - M2 adds Trivy/Syft/cosign on top of this image.
# =============================================================================
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS runtime

RUN groupadd --system palisade && useradd --system --gid palisade --no-create-home palisade

COPY --from=builder /venv /venv
WORKDIR /app
COPY app ./app

ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER palisade
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
