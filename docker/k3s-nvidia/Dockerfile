# syntax=docker/dockerfile:1.7-labs
# =============================================================================
#  k3s node image with the NVIDIA container runtime baked in.
#
#  Why this exists:
#    The stock rancher/k3s image has no NVIDIA container runtime, so containerd
#    inside the node cannot hand a GPU to a pod - even when the node container
#    itself was started with `--gpus all`. We therefore rebuild the k3s rootfs
#    on top of a CUDA base image that has nvidia-container-toolkit installed.
#
#    On startup k3s scans for known container runtimes; finding
#    nvidia-container-runtime it writes a containerd config exposing it and
#    creates the `nvidia` RuntimeClass automatically.
#
#  Build with: make k3s-image
# =============================================================================

ARG K3S_TAG=v1.36.4-k3s1
ARG CUDA_TAG=12.8.1-base-ubuntu24.04

FROM rancher/k3s:${K3S_TAG} AS k3s
FROM nvidia/cuda:${CUDA_TAG}

ARG DEBIAN_FRONTEND=noninteractive

# --- NVIDIA container toolkit ------------------------------------------------
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl gnupg2 ca-certificates \
 && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
      | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
 && curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
      | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
      > /etc/apt/sources.list.d/nvidia-container-toolkit.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends nvidia-container-toolkit \
 && rm -rf /var/lib/apt/lists/*

# --- overlay the k3s rootfs --------------------------------------------------
# /bin is copied separately because the CUDA image needs its own /bin to remain
# usable during the build; k3s ships its binaries there and would clobber it.
COPY --from=k3s / / --exclude=/bin
COPY --from=k3s /bin /bin

# --- k3s runtime expectations ------------------------------------------------
VOLUME /var/lib/kubelet
VOLUME /var/lib/rancher/k3s
VOLUME /var/lib/cni
VOLUME /var/log

ENV PATH="$PATH:/bin/aux"
ENV CRI_CONFIG_FILE=/var/lib/rancher/k3s/agent/etc/crictl.yaml

ENTRYPOINT ["/bin/k3s"]
CMD ["agent"]
