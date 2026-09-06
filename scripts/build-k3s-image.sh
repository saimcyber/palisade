#!/usr/bin/env bash
# Build the GPU-capable k3s node image. Separated from cluster-up.sh so it can
# be rebuilt on its own when the k3s or CUDA version is bumped.
set -euo pipefail

K3S_TAG="${K3S_TAG:-v1.36.4-k3s1}"
CUDA_TAG="${CUDA_TAG:-12.8.1-base-ubuntu24.04}"
IMAGE="${K3S_IMAGE:-palisade/k3s-nvidia:${K3S_TAG}}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Building ${IMAGE}"
echo "  k3s:  ${K3S_TAG}"
echo "  cuda: ${CUDA_TAG}"

DOCKER_BUILDKIT=1 docker build \
  --build-arg "K3S_TAG=${K3S_TAG}" \
  --build-arg "CUDA_TAG=${CUDA_TAG}" \
  -t "${IMAGE}" \
  "${ROOT}/docker/k3s-nvidia"

echo "Built ${IMAGE}"
