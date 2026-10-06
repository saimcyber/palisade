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
FROM python:3.12-slim@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe

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
