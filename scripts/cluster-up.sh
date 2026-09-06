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
#
#  GPU strategy differs by host, and the difference is deliberate:
#    WSL2          -> CDI injection      (device plugin cannot work; NVML is
#                                         unsupported against /dev/dxg)
#    native Linux  -> NVIDIA device plugin, giving real scheduler accounting
#  See docs/adr/0002-gpu-in-k3d.md.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
PROFILE="${PROFILE:-lite}"
K3S_TAG="${K3S_TAG:-v1.36.4-k3s1}"
K3S_IMAGE="${K3S_IMAGE:-palisade/k3s-nvidia:${K3S_TAG}}"
DEVICE_PLUGIN_VERSION="${DEVICE_PLUGIN_VERSION:-v0.20.0}"
CUDA_IMAGE="${CUDA_IMAGE:-nvidia/cuda:12.8.1-base-ubuntu24.04}"
API_PORT="${API_PORT:-6550}"
HTTP_PORT="${HTTP_PORT:-8080}"
HTTPS_PORT="${HTTPS_PORT:-8443}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; CYA='\033[36m'; RST='\033[0m'
step() { printf '\n%b==>%b %s\n' "$CYA" "$RST" "$*"; }
ok()   { printf '  %bok%b   %s\n' "$GREEN" "$RST" "$*"; }
die()  { printf '  %bfail%b %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
note() { printf '  %bnote%b %s\n' "$YEL" "$RST" "$*"; }

IS_WSL=0
grep -qi microsoft /proc/version 2>/dev/null && IS_WSL=1

# --- preflight ---------------------------------------------------------------
step "Preflight"
command -v docker >/dev/null || die "docker not found"
docker info >/dev/null 2>&1 || die "docker daemon unreachable - start Docker Desktop and enable WSL integration"
command -v k3d >/dev/null || die "k3d not found - run: make tools"
ok "docker + k3d present"
[ "$IS_WSL" = "1" ] && ok "host is WSL2 - will use CDI for GPU injection"

GPU_OK=0
if docker run --rm --gpus all "$CUDA_IMAGE" nvidia-smi -L >/dev/null 2>&1; then
  GPU_OK=1
  ok "docker can pass through the GPU"
else
  note "docker cannot pass through the GPU - creating a CPU-only cluster"
  note "see docs/adr/0002-gpu-in-k3d.md for the external-backend fallback"
fi

# --- node image --------------------------------------------------------------
if [ "$GPU_OK" = "1" ]; then
  if ! docker image inspect "$K3S_IMAGE" >/dev/null 2>&1; then
    step "Building the GPU-capable k3s node image (first run only)"
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

# --- GPU wiring --------------------------------------------------------------
if [ "$GPU_OK" = "1" ]; then
  # k3s writes its RuntimeClasses a few seconds after the node reports Ready,
  # so this has to wait rather than check once.
  step "Waiting for the nvidia RuntimeClass"
  RC_OK=0
  for i in $(seq 1 30); do
    if kubectl get runtimeclass nvidia >/dev/null 2>&1; then RC_OK=1; break; fi
    sleep 2
  done
  if [ "$RC_OK" = "1" ]; then
    ok "RuntimeClass nvidia present"
  else
    note "RuntimeClass nvidia not created - k3s did not detect the NVIDIA runtime"
    note "check: docker exec k3d-${CLUSTER}-server-0 grep -i nvidia \\"
    note "         /var/lib/rancher/k3s/agent/etc/containerd/config.toml"
  fi

  if [ "$IS_WSL" = "1" ]; then
    # ---- WSL2: CDI ----------------------------------------------------------
    bash "$ROOT/scripts/setup-gpu-cdi.sh"
  else
    # ---- native Linux: device plugin ---------------------------------------
    step "Installing the NVIDIA device plugin"
    # The chart's default node affinity expects a label normally applied by
    # NVIDIA's Node Feature Discovery. GFD is disabled here to save memory, so
    # the label is applied by hand - otherwise the DaemonSet wants 0 nodes.
    kubectl label node --all nvidia.com/gpu.present=true --overwrite >/dev/null
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
      if [ -n "$CAP" ] && [ "$CAP" != "0" ]; then ok "node advertises ${CAP} GPU(s)"; break; fi
      sleep 4
      [ "$i" = "30" ] && note "GPU not advertised - kubectl -n kube-system logs -l app.kubernetes.io/name=nvidia-device-plugin"
    done
  fi
fi

# --- summary -----------------------------------------------------------------
step "Cluster ready"
kubectl get nodes -o wide
printf "\n  Ingress HTTP  -> http://localhost:%s\n" "$HTTP_PORT"
printf "  Ingress HTTPS -> https://localhost:%s\n" "$HTTPS_PORT"
printf '\n  Next: %bmake gpu-check%b\n\n' "$CYA" "$RST"
