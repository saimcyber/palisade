#!/usr/bin/env bash
# =============================================================================
#  Palisade - provision the age private key Argo CD's SOPS plugin needs
#
#  WHY THIS EXISTS
#  ----------------
#  deploy/secrets/*.enc.yaml is encrypted to a public age key committed in
#  .sops.yaml - anyone can encrypt a new secret against it. Only the
#  matching private key can decrypt one, and that key is never committed
#  (docs/adr/0015). Something still has to get it into the cluster, once,
#  by hand, exactly the same "secrets to create secrets need one
#  non-GitOps bootstrap step" pattern M2's AWS identity used
#  (docs/adr/0009) - this script is that step for SOPS.
#
#  Safe to re-run: if the argocd namespace already has the sops-age
#  secret, this does nothing.
# =============================================================================
set -euo pipefail

NAMESPACE="${NAMESPACE:-argocd}"
KEY_FILE="${AGE_KEY_FILE:-$HOME/.config/palisade/age.key}"

GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'
ok()   { printf '  %bok%b   %s\n' "$GREEN" "$RST" "$*"; }
note() { printf '  %bnote%b %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %bfail%b %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n%b==>%b %s\n' "$CYA" "$RST" "$*"; }

command -v age-keygen >/dev/null || die "age-keygen not found"
command -v kubectl >/dev/null || die "kubectl not found"

step "Checking for an existing key at $KEY_FILE"
if [ -f "$KEY_FILE" ]; then
  ok "found - reusing it, not generating a new one"
else
  note "not found - generating a new age keypair"
  mkdir -p "$(dirname "$KEY_FILE")"
  age-keygen -o "$KEY_FILE"
  pub="$(grep -oE 'age1[a-z0-9]+' "$KEY_FILE" | head -1)"
  note "public key: $pub"
  note "add this to .sops.yaml's age: field if it isn't there already,"
  note "and re-encrypt every file under deploy/secrets/ against it."
fi
chmod 600 "$KEY_FILE"

step "Checking for the sops-age Secret in namespace '$NAMESPACE'"
if kubectl get secret sops-age -n "$NAMESPACE" >/dev/null 2>&1; then
  ok "already provisioned - nothing to do"
  exit 0
fi
note "not found - creating it"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl create secret generic sops-age \
  --namespace "$NAMESPACE" \
  --from-file=key.txt="$KEY_FILE"
ok "provisioned - the repo-server's SOPS plugin can now decrypt deploy/secrets/*.enc.yaml"
