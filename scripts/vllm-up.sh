#!/usr/bin/env bash
# =============================================================================
#  M1 acceptance test (part 2): vLLM serving Qwen3-0.6B, in-cluster, on the
#  RTX 3050 through the CDI path.
#
#  The image is pulled directly by the node's own containerd rather than via
#  `k3d image import` (docker save | ctr import). vllm/vllm-openai is a
#  multi-arch manifest list; on this containerd-snapshotter-backed Docker,
#  `docker save` exports a reference to the arm64 sub-manifest even though
#  only the amd64 layers were ever pulled locally, and `ctr images import`
#  then fails with "content digest ... not found". Pulling straight from the
#  registry inside the node, restricted to --platform linux/amd64, sidesteps
#  the whole class of bug and is also lower peak memory (streamed layer by
#  layer) than importing a single ~9 GB tar in one shot.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
CTX="k3d-${CLUSTER}"
NODE="k3d-${CLUSTER}-server-0"
NS="${NS:-default}"
IMG="docker.io/vllm/vllm-openai:v0.28.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[32m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'

printf '\n%b==>%b Checking whether %s is already in the node\n' "$CYA" "$RST" "$IMG"
if docker exec "$NODE" crictl images 2>/dev/null | grep -q 'vllm-openai *v0.28.0'; then
  echo "  already present - skipping the pull"
else
  printf '%b==>%b Pulling %s directly into the node (this is ~9 GB, be patient)\n' "$CYA" "$RST" "$IMG"
  docker exec "$NODE" ctr -n k8s.io images pull --platform linux/amd64 "$IMG"
fi

printf '%b==>%b Applying k8s/vllm.yaml\n' "$CYA" "$RST"
kubectl --context "$CTX" -n "$NS" apply -f "$ROOT/k8s/vllm.yaml" >/dev/null

printf '%b==>%b Waiting for the model to load (cold HF download can take a while; a\n' "$CYA" "$RST"
echo "    warm PVC cache is much faster - see the startupProbe budget in k8s/vllm.yaml)"
if kubectl --context "$CTX" -n "$NS" wait --for=condition=ready pod -l app.kubernetes.io/name=vllm --timeout=600s >/dev/null 2>&1; then
  printf '\n%bvLLM is up%b - palisade-small is serving on the RTX 3050.\n\n' "$GREEN" "$RST"
  echo "Try it:"
  echo "  kubectl --context $CTX port-forward svc/vllm 8000:8000"
  echo "  curl localhost:8000/v1/models"
  exit 0
fi

printf '\n%bvLLM DID NOT BECOME READY%b\n\n' "$RED" "$RST"
echo "--- pod events ---"
kubectl --context "$CTX" -n "$NS" describe pod -l app.kubernetes.io/name=vllm | tail -30
echo ""
echo "--- logs ---"
kubectl --context "$CTX" -n "$NS" logs -l app.kubernetes.io/name=vllm --tail=40 || true
echo ""
echo "Known failure modes (see docs/CONVENTIONS.md and docs/adr/0003-vllm-over-alternatives.md):"
echo "  - RuntimeError: UVA is not available -> VLLM_WSL2_ENABLE_PIN_MEMORY=1 missing"
echo "  - torch.OutOfMemoryError at KV-cache allocation -> lower --kv-cache-memory-bytes"
echo "  - ValueError: VLLM_PORT '...' appears to be a URI -> enableServiceLinks: false missing"
exit 1
