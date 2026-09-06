#!/usr/bin/env bash
# =============================================================================
#  Palisade - environment doctor
#
#  Verifies the whole local development environment in one shot. Exits non-zero
#  if anything required is missing, so CI (and `make doctor`) can gate on it.
# =============================================================================
set -uo pipefail

PASS=0; FAIL=0; WARN=0
GREEN='\033[32m'; RED='\033[31m'; YEL='\033[33m'; DIM='\033[90m'; CYA='\033[36m'; RST='\033[0m'

hdr()  { printf "\n${CYA}%s${RST}\n" "$*"; }
pass() { printf "  ${GREEN}PASS${RST}  %-22s ${DIM}%s${RST}\n" "$1" "${2:-}"; PASS=$((PASS+1)); }
fail() { printf "  ${RED}FAIL${RST}  %-22s ${DIM}%s${RST}\n" "$1" "${2:-}"; FAIL=$((FAIL+1)); }
warn() { printf "  ${YEL}WARN${RST}  %-22s ${DIM}%s${RST}\n" "$1" "${2:-}"; WARN=$((WARN+1)); }

# check <label> <command that prints a version>
check() {
  local label="$1"; shift
  if command -v "$label" >/dev/null 2>&1; then
    pass "$label" "$( "$@" 2>/dev/null | head -1 )"
  else
    fail "$label" "not installed - run: make tools"
  fi
}

printf "\n${CYA}Palisade environment check${RST}\n"

# --- host --------------------------------------------------------------------
hdr "Host"
if grep -qi microsoft /proc/version 2>/dev/null; then
  pass "WSL2" "$(uname -r)"
else
  warn "WSL2" "not running under WSL - that is fine on native Linux"
fi
CPUS=$(nproc)
MEM_GB=$(awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo)
[ "$CPUS" -ge 4 ] && pass "cpus" "${CPUS} logical" || warn "cpus" "${CPUS} - expect slow builds"
awk -v m="$MEM_GB" 'BEGIN{exit !(m>=7)}' \
  && pass "memory" "${MEM_GB} GB visible to Linux" \
  || warn "memory" "${MEM_GB} GB - tight; use make up-lite"

DISK_AVAIL=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
[ "${DISK_AVAIL:-0}" -ge 25 ] \
  && pass "disk" "${DISK_AVAIL} GB free in \$HOME" \
  || warn "disk" "${DISK_AVAIL} GB free - vLLM images need ~15 GB"

# --- GPU ---------------------------------------------------------------------
hdr "GPU"
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
  GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
  GPU_DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
  if [ -n "$GPU_NAME" ]; then
    pass "nvidia-smi (host)" "$GPU_NAME / $GPU_MEM / driver $GPU_DRV"
  else
    fail "nvidia-smi (host)" "present but returned no GPU"
  fi
else
  fail "nvidia-smi (host)" "no GPU visible inside Linux"
fi

# --- container runtime -------------------------------------------------------
hdr "Container runtime"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    pass "docker" "$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
    # GPU passthrough into a container is the single most important check here.
    if docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 \
         nvidia-smi --query-gpu=name --format=csv,noheader >/dev/null 2>&1; then
      pass "docker --gpus all" "container can see the GPU"
    else
      fail "docker --gpus all" "container cannot see the GPU (see docs/adr/0002)"
    fi
  else
    fail "docker" "daemon not reachable - is Docker Desktop running with WSL integration on?"
  fi
else
  fail "docker" "not on PATH - enable Docker Desktop WSL integration for this distro"
fi

# --- toolchain ---------------------------------------------------------------
hdr "Toolchain"
check kubectl   kubectl version --client -o yaml
check helm      helm version --template '{{.Version}}'
check k3d       k3d version
check terraform terraform version
check k6        k6 version
check cosign    cosign version --json
check syft      syft version
check trivy     trivy --version
check sops      sops --version
check age       age --version
check yq        yq --version
check jq        jq --version
check argocd    argocd version --client --short
check kustomize kustomize version
check aws       aws --version
check git       git --version
check make      make --version
check python3   python3 --version

# --- cluster -----------------------------------------------------------------
hdr "Cluster"
if command -v k3d >/dev/null 2>&1 && k3d cluster list 2>/dev/null | grep -q '^palisade'; then
  pass "k3d cluster" "$(k3d cluster list palisade --no-headers 2>/dev/null)"
  if kubectl --context k3d-palisade get nodes >/dev/null 2>&1; then
    if kubectl --context k3d-palisade get runtimeclass nvidia >/dev/null 2>&1; then
      pass "RuntimeClass nvidia" "present"
    else
      fail "RuntimeClass nvidia" "missing - node image lacks the NVIDIA runtime"
    fi
    # On WSL2 the GPU arrives via CDI, not as an allocatable resource.
    # See docs/adr/0002-gpu-in-k3d.md for why the device plugin cannot work.
    if grep -qi microsoft /proc/version 2>/dev/null; then
      if docker exec k3d-palisade-server-0 test -f /etc/cdi/nvidia.yaml 2>/dev/null; then
        if docker exec k3d-palisade-server-0 grep -q libdxcore.so /etc/cdi/nvidia.yaml 2>/dev/null; then
          pass "CDI spec" "present, includes libdxcore.so"
        else
          fail "CDI spec" "missing libdxcore.so - run: make gpu-cdi"
        fi
      else
        fail "CDI spec" "absent - run: make gpu-cdi"
      fi
    else
      GPUCAP=$(kubectl --context k3d-palisade get nodes -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}' 2>/dev/null)
      if [ -n "$GPUCAP" ] && [ "$GPUCAP" != "0" ]; then
        pass "nvidia.com/gpu" "${GPUCAP} allocatable in-cluster"
      else
        warn "nvidia.com/gpu" "0 allocatable - device plugin not ready"
      fi
    fi
  else
    warn "kubectl context" "cluster exists but is not reachable"
  fi
else
  warn "k3d cluster" "not created yet - run: make up"
fi

# --- summary -----------------------------------------------------------------
printf "\n${CYA}Summary${RST}  ${GREEN}%d passed${RST}  ${YEL}%d warnings${RST}  ${RED}%d failed${RST}\n\n" \
  "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
