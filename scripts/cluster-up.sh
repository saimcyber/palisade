#!/usr/bin/env bash
# =============================================================================
#  Palisade - create the local k3d cluster
#
#  PROFILE=lite  cluster + GPU support only          (default, ~2 GB)
#  PROFILE=full  adds Argo CD + observability later  (~5 GB)
#
#  The profile split exists because the whole WSL2 VM is capped at 10 GB, and
#  the observability stack plus Argo CD will not co-exist comfortably with a
#  GPU workload on a 16 GB laptop. Turning off what you are not working on is
#  a legitimate operational decision, not a shortcut.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
PROFILE="${PROFILE:-lite}"
K3S_TAG="${K3S_TAG:-v1.31.5-k3s1}"
K3S_IMAGE="${K3S_IMAGE:-palisade/k3s-nvidia:${K3S_TAG}}"
DEVICE_PLUGIN_VERSION="${DEVICE_PLUGIN_VERSION:-v0.17.0}"
API_PORT="${API_PORT:-6550}"
HTTP_PORT="${HTTP_PORT:-8080}"
HTTPS_PORT="${HTTPS_PORT:-8443}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; CYA='\033[36m'; RST='\033[0m'
step() { printf "\n${CYA}==>${RST} %s\n" "$*"; }
ok()   { printf "  ${GREEN}ok${RST}   %s\n" "$*"; }
die()  { printf "  ${RED}fail${RST} %s\n" "$*" >&2; exit 1; }
note() { printf "  ${YEL}note${RST} %s\n" "$*"; }

# --- preflight ---------------------------------------------------------------
step "Preflight"
command -v docker >/dev/null || die "docker not found"
docker info >/dev/null 2>&1 || die "docker daemon unreachable - start Docker Desktop and enable WSL integration"
command -v k3d >/dev/null || die "k3d not found - run: make tools"
ok "docker + k3d present"

GPU_OK=0
if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi -L >/dev/null 2>&1; then
  GPU_OK=1
  ok "docker can pass through the GPU"
else
  note "docker cannot pass through the GPU - creating a CPU-only cluster"
  note "see docs/adr/0002-gpu-in-k3d.md for the external-backend fallback"
fi

# --- node image --------------------------------------------------------------
if [ "$GPU_OK" = "1" ]; then
  if ! docker image inspect "$K3S_IMAGE" >/dev/null 2>&1; then
    step "Building the GPU-capable k3s node image (first run only, ~4 min)"
    bash "$ROOT/scripts/build-k3s-image.sh"
  else
    ok "node image $K3S_IMAGE already built"
  fi
fi

# --- cluster -----------------------------------------------------------------
if k3d cluster list 2>/dev/null | awk '{print $1}' | grep -qx "$CLUSTER"; then
  ok "cluster '$CLUSTER' already exists"
else
  step "Creating k3d cluster '$CLUSTER' (profile: $PROFILE)"
  args=(
    cluster create "$CLUSTER"
    --api-port "$API_PORT"
    --port "${HTTP_PORT}:80@loadbalancer"
    --port "${HTTPS_PORT}:443@loadbalancer"
    --agents 0
    --k3s-arg "--disable=metrics-server@server:0"
    --wait
  )
  if [ "$GPU_OK" = "1" ]; then
    args+=( --image "$K3S_IMAGE" --gpus all )
  fi
  k3d "${args[@]}"
  ok "cluster created"
fi

k3d kubeconfig merge "$CLUSTER" --kubeconfig-switch-context >/dev/null
ok "kubectl context -> k3d-${CLUSTER}"

step "Waiting for the node to become Ready"
kubectl wait --for=condition=Ready node --all --timeout=180s >/dev/null
ok "node Ready"

# --- GPU device plugin -------------------------------------------------------
if [ "$GPU_OK" = "1" ]; then
  step "Installing the NVIDIA device plugin"
  # RuntimeClass 'nvidia' is created by k3s when it detects the runtime in the
  # node image. The device plugin must run under it to advertise nvidia.com/gpu.
  if ! kubectl get runtimeclass nvidia >/dev/null 2>&1; then
    note "RuntimeClass 'nvidia' missing - k3s did not detect the runtime"
    note "check: docker exec k3d-${CLUSTER}-server-0 grep -i nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml"
  fi
  helm repo add nvdp https://nvidia.github.io/k8s-device-plugin >/dev/null 2>&1 || true
  helm repo update nvdp >/dev/null 2>&1 || true
  helm upgrade --install nvdp nvdp/nvidia-device-plugin \
    --namespace kube-system \
    --version "${DEVICE_PLUGIN_VERSION#v}" \
    --set runtimeClassName=nvidia \
    --set gfd.enabled=false \
    --wait --timeout 4m >/dev/null
  ok "device plugin installed"

  step "Waiting for nvidia.com/gpu to be advertised"
  for i in $(seq 1 30); do
    CAP=$(kubectl get nodes -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}' 2>/dev/null || true)
    if [ -n "$CAP" ] && [ "$CAP" != "0" ]; then
      ok "node advertises ${CAP} GPU(s)"
      break
    fi
    sleep 4
    [ "$i" = "30" ] && note "GPU not advertised after 2m - run: kubectl -n kube-system logs -l app.kubernetes.io/name=nvidia-device-plugin"
  done
fi

# --- summary -----------------------------------------------------------------
step "Cluster ready"
kubectl get nodes -o wide
printf "\n  Ingress HTTP  -> http://localhost:%s\n" "$HTTP_PORT"
printf "  Ingress HTTPS -> https://localhost:%s\n" "$HTTPS_PORT"
printf "\n  Next: ${CYA}make gpu-check${RST}\n\n"
