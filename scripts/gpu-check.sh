#!/usr/bin/env bash
# =============================================================================
#  M0 acceptance test: a pod scheduled by Kubernetes must see the RTX 3050.
#
#  This is the gate for the whole project. If this passes, every later
#  milestone has somewhere to run. If it does not, we fall back to the
#  external model backend documented in docs/adr/0002-gpu-in-k3d.md.
# =============================================================================
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
CTX="k3d-${CLUSTER}"
NS="${NS:-default}"
JOB=gpu-check
GREEN='\033[32m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'

kubectl --context "$CTX" -n "$NS" delete job "$JOB" --ignore-not-found >/dev/null 2>&1

printf "\n${CYA}==>${RST} Submitting the GPU check job\n"
kubectl --context "$CTX" -n "$NS" apply -f "$(dirname "${BASH_SOURCE[0]}")/../k8s/gpu-check.yaml" >/dev/null

printf "${CYA}==>${RST} Waiting for completion (up to 3 min)\n"
if kubectl --context "$CTX" -n "$NS" wait --for=condition=complete "job/$JOB" --timeout=180s >/dev/null 2>&1; then
  echo ""
  kubectl --context "$CTX" -n "$NS" logs "job/$JOB"
  printf "\n${GREEN}M0 ACCEPTANCE PASSED${RST} - Kubernetes scheduled a pod that can see the GPU.\n\n"
  kubectl --context "$CTX" -n "$NS" delete job "$JOB" >/dev/null 2>&1 || true
  exit 0
fi

printf "\n${RED}M0 ACCEPTANCE FAILED${RST}\n\n"
echo "--- job description ---"
kubectl --context "$CTX" -n "$NS" describe job "$JOB" | tail -25
echo ""
echo "--- pod events ---"
kubectl --context "$CTX" -n "$NS" describe pod -l job-name="$JOB" | tail -30
echo ""
echo "--- logs (if any) ---"
kubectl --context "$CTX" -n "$NS" logs "job/$JOB" 2>&1 | tail -20 || true
echo ""
echo "Next steps: see docs/adr/0002-gpu-in-k3d.md"
exit 1
