#!/usr/bin/env bash
# =============================================================================
#  M1 acceptance test (part 1): a real CUDA kernel must execute through the
#  CDI path and produce a numerically verified result - not just be visible
#  to nvidia-smi (that is M0's gpu-check).
#
#  Builds docker/cuda-check, imports it into the cluster's containerd (k3d
#  clusters do not share the host's image store), and runs it as a Job.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
CTX="k3d-${CLUSTER}"
NS="${NS:-default}"
JOB=cuda-check
IMG=palisade/cuda-check:latest
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[32m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'

printf '%b==>%b Building %s\n' "$CYA" "$RST" "$IMG"
docker build -t "$IMG" "$ROOT/docker/cuda-check" >/dev/null

printf '%b==>%b Importing into cluster %s\n' "$CYA" "$RST" "$CLUSTER"
k3d image import "$IMG" -c "$CLUSTER" >/dev/null

kubectl --context "$CTX" -n "$NS" delete job "$JOB" --ignore-not-found >/dev/null 2>&1

printf '%b==>%b Submitting the CUDA compute check job\n' "$CYA" "$RST"
kubectl --context "$CTX" -n "$NS" apply -f "$ROOT/k8s/cuda-check.yaml" >/dev/null

printf '%b==>%b Waiting for the job to complete\n' "$CYA" "$RST"
if kubectl --context "$CTX" -n "$NS" wait --for=condition=complete "job/$JOB" --timeout=180s >/dev/null 2>&1; then
  echo ""
  kubectl --context "$CTX" -n "$NS" logs "job/$JOB"
  printf '\n%bM1 CUDA-CHECK PASSED%b - a real kernel ran through the CDI path.\n\n' "$GREEN" "$RST"
  kubectl --context "$CTX" -n "$NS" delete job "$JOB" >/dev/null 2>&1 || true
  exit 0
fi

printf '\n%bM1 CUDA-CHECK FAILED%b\n\n' "$RED" "$RST"
echo "--- job description ---"
kubectl --context "$CTX" -n "$NS" describe job "$JOB" | tail -25
echo ""
echo "--- pod events ---"
kubectl --context "$CTX" -n "$NS" describe pod -l job-name="$JOB" | tail -30
echo ""
echo "--- logs (if any) ---"
kubectl --context "$CTX" -n "$NS" logs "job/$JOB" 2>&1 | tail -20 || true
echo ""
echo "Next steps: compare 'ldd' inside the pod against the host driver store and"
echo "extend scripts/setup-gpu-cdi.sh (this is the same class of gap that"
echo "libdxcore.so closed for nvidia-smi in M0). See docs/adr/0002-gpu-in-k3d.md."
exit 1
