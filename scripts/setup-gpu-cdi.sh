#!/usr/bin/env bash
# =============================================================================
#  Palisade - wire the GPU into the cluster using CDI
#
#  WHY THIS EXISTS
#  ---------------
#  On a normal Linux host you install the NVIDIA device plugin, it advertises
#  `nvidia.com/gpu` as an allocatable resource, and pods request it. That path
#  does NOT work under WSL2: the device plugin discovers GPUs through NVML, and
#  NVML is not supported against WSL's /dev/dxg driver model. The plugin starts,
#  fails `nvml init failed: Not Supported`, and crash-loops forever.
#
#  What does work is CDI (Container Device Interface). `nvidia-ctk` detects WSL,
#  finds the Windows driver store mounted into the VM, and writes a spec that
#  tells containerd exactly which device nodes and libraries to inject.
#
#  One bug has to be worked around: nvidia-ctk looks for libdxcore.so inside the
#  WSL driver store, but Docker Desktop places it in /usr/lib/x86_64-linux-gnu.
#  Generation logs "Could not locate libdxcore.so" and continues, producing a
#  spec that mounts nvidia-smi but not the library it needs - so the container
#  gets a working binary that reports "Failed to initialize NVML: N/A". We
#  append the missing mount ourselves.
#
#  This runs against a LIVE node container, not at image build time, because the
#  driver store path is host-specific and only knowable at runtime.
#
#  See docs/adr/0002-gpu-in-k3d.md for the full write-up.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
NODE="${NODE:-k3d-${CLUSTER}-server-0}"
SPEC=/etc/cdi/nvidia.yaml
DXCORE=/usr/lib/x86_64-linux-gnu/libdxcore.so

GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'
ok()   { printf "  ${GREEN}ok${RST}   %s\n" "$*"; }
note() { printf "  ${YEL}note${RST} %s\n" "$*"; }
die()  { printf "  ${RED}fail${RST} %s\n" "$*" >&2; exit 1; }
step() { printf "\n${CYA}==>${RST} %s\n" "$*"; }

docker inspect "$NODE" >/dev/null 2>&1 || die "node container '$NODE' not found"

step "Generating the CDI spec inside $NODE"
docker exec "$NODE" sh -c "mkdir -p /etc/cdi && nvidia-ctk cdi generate --output=${SPEC}" >/dev/null 2>&1 \
  || die "nvidia-ctk cdi generate failed - is the GPU visible in the node? try: docker exec $NODE nvidia-smi -L"
ok "spec written to ${SPEC}"

# --- work around the missing libdxcore.so ------------------------------------
if docker exec "$NODE" sh -c "grep -q '${DXCORE}' ${SPEC}"; then
  ok "libdxcore.so already present in the spec"
elif docker exec "$NODE" sh -c "test -f ${DXCORE}"; then
  docker exec "$NODE" sh -c "cat >> ${SPEC} <<'EOF'
        - hostPath: ${DXCORE}
          containerPath: ${DXCORE}
          options:
            - ro
            - nosuid
            - nodev
            - rbind
            - rprivate
EOF"
  ok "appended libdxcore.so mount (works around the nvidia-ctk WSL gap)"
else
  note "libdxcore.so not found at ${DXCORE} - NVML may fail inside pods"
fi

# --- pin the runtime to CDI mode ---------------------------------------------
# 'auto' resolves to wsl mode, which is less deterministic than being explicit.
docker exec "$NODE" sh -c \
  "sed -i 's/^mode = \"auto\"/mode = \"cdi\"/' /etc/nvidia-container-runtime/config.toml" || true
ok "nvidia-container-runtime mode = cdi"

step "GPU wiring complete"
printf "  Pods need BOTH of these to receive the GPU:\n"
printf "    runtimeClassName: nvidia\n"
printf "    annotation  cdi.k8s.io/gpu: \"nvidia.com/gpu=all\"\n\n"
