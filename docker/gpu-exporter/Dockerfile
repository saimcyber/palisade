# =============================================================================
#  Palisade GPU exporter - replaces the third-party
#  utkuozdemir/nvidia_gpu_exporter (ADR 0023's original choice).
#
#  WHY THIS EXISTS
#  ----------------
#  That image shipped no shell and no /usr/bin at all - confirmed directly
#  (even `ls` fails inside it) - which looked like the whole story. It
#  wasn't: a from-scratch test with a perfectly ordinary base image
#  (python:3.12-slim, same base this project already builds/scans/trusts
#  for the gateway) *still* came up with no nvidia-smi. The real cause,
#  found by diffing this pod against the known-working gpu-check Job
#  (k8s/gpu-check.yaml): nvidia-container-runtime's CDI hook only injects
#  the "utility" driver capability - which is what carries nvidia-smi -
#  when NVIDIA_DRIVER_CAPABILITIES says to. nvidia/cuda-based images set
#  that by default; nothing else does, including this image before this
#  comment was written. The two ENV lines below are the actual fix; the
#  earlier full-filesystem rebuild was a real improvement but not
#  sufficient on its own. See ADR 0023 for the full investigation.
#
#  No pip dependencies: the whole exporter is subprocess + http.server.
# =============================================================================
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54

# Debian security updates applied at build time, not left to whenever the
# upstream base is next republished: a base digest can lag a published fix
# by days (seen: zlib CVE-2026-76844/85091 fixed in deb13u1, base still on
# +b1). The resulting image is still pinned by digest, and its SBOM records
# the exact package versions that went in.
RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN groupadd --system gpuexp && useradd --system --gid gpuexp --no-create-home gpuexp

WORKDIR /app
COPY exporter.py .

# The actual fix (see header) - tells nvidia-container-runtime's CDI hook
# to inject the "utility" capability (nvidia-smi + NVML), the same thing
# nvidia/cuda base images set that this image doesn't inherit otherwise.
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=utility \
    PYTHONUNBUFFERED=1

USER gpuexp
EXPOSE 9835

CMD ["python3", "exporter.py"]
