#!/usr/bin/env bash
# =============================================================================
#  Palisade - bootstrap GitOps on a running cluster (after `make up`)
#
#  The only non-GitOps steps in the whole deployment, in the order they
#  have to happen. After this, git is the only route to the cluster.
#
#    1. age key Secret        - before Argo CD: repo-server mounts it, and
#                               would sit in ContainerCreating without it
#    2. Argo CD + Kyverno     - Terraform Helm provider (infra/terraform/cluster)
#    3. Kyverno ready         - its webhooks must answer before anything
#                               syncs, or the first pods are never checked
#    4. vLLM image pre-pull   - optional speed-up; see CLAUDE.md for why it is
#                               `ctr pull` and not `k3d image import`
#    5. root Application      - app-of-apps; policies (wave -1) -> secrets
#                               (wave 0) -> workloads (wave 1), ADR 0020
#    6. wait                  - until every Application is Synced + Healthy
#
#  Safe to re-run: every step is idempotent against a cluster that already
#  has it.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER="${CLUSTER:-palisade}"
NODE="k3d-${CLUSTER}-server-0"
WAIT_SECONDS="${WAIT_SECONDS:-2400}"
PREPULL="${PREPULL:-1}"
GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'
ok()   { printf '  %bok%b   %s\n' "$GREEN" "$RST" "$*"; }
note() { printf '  %bnote%b %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %bfail%b %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n%b==>%b %s\n' "$CYA" "$RST" "$*"; }

for t in kubectl terraform docker; do command -v "$t" >/dev/null || die "$t not found"; done
kubectl get nodes >/dev/null 2>&1 || die "cluster unreachable - run 'make up' first"

step "1/6  age key for the SOPS plugin"
bash "$ROOT/scripts/setup-sops-age.sh"

step "2/6  Argo CD + Kyverno (Terraform Helm provider)"
terraform -chdir="$ROOT/infra/terraform/cluster" init -input=false >/dev/null
terraform -chdir="$ROOT/infra/terraform/cluster" apply -input=false -auto-approve
ok "applied"

step "3/6  Waiting for Kyverno and Argo CD to be Available"
kubectl -n kyverno wait --for=condition=Available deploy --all --timeout=300s >/dev/null
kubectl -n argocd wait --for=condition=Available deploy --all --timeout=300s >/dev/null
ok "both controllers up"

step "4/6  Pre-pulling the vLLM image into the node"
if [ "$PREPULL" = "1" ]; then
  img="$(awk '/^vllm:/{v=1} v&&/repository:/{r=$2} v&&/tag:/{print "docker.io/" r ":" $2; exit}' \
    "$ROOT/deploy/charts/palisade/values.yaml")"
  if docker exec "$NODE" ctr -n k8s.io images ls -q | grep -qx "$img"; then
    ok "$img already present"
  else
    note "pulling $img (large - streamed layer by layer)"
    docker exec "$NODE" ctr -n k8s.io images pull --platform linux/amd64 "$img" >/dev/null
    ok "pulled"
  fi
else
  note "skipped (PREPULL=0) - the kubelet will pull it on first schedule"
fi

step "5/6  Root Application (app-of-apps)"
kubectl apply -f "$ROOT/deploy/argocd/root-app.yaml"

step "6/6  Waiting for every Application to be Synced + Healthy"
deadline=$(( $(date +%s) + WAIT_SECONDS ))
while :; do
  apps="$(kubectl -n argocd get applications \
    -o jsonpath='{range .items[*]}{.metadata.name}={.status.sync.status}/{.status.health.status}{"\n"}{end}' 2>/dev/null || true)"
  total=$(printf '%s\n' "$apps" | grep -c = || true)
  good=$(printf '%s\n' "$apps" | grep -c '=Synced/Healthy$' || true)
  if [ "$total" -ge 4 ] && [ "$good" = "$total" ]; then break; fi
  [ "$(date +%s)" -gt "$deadline" ] && { printf '%s\n' "$apps"; die "not converged - kubectl -n argocd get applications"; }
  sleep 15
done
kubectl -n argocd get applications
kubectl -n palisade get pods
printf '\n  %bGitOps is up.%b From here on, change the cluster by pushing to main.\n\n' "$GREEN" "$RST"
