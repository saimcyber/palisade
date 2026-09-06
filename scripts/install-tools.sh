#!/usr/bin/env bash
# =============================================================================
#  Palisade - toolchain installer
#
#  Idempotent and version-aware: it compares the installed version against the
#  pin below and reinstalls only on a mismatch. Pinning matters for the same
#  reason it matters in CI - "latest" is not a version you can reproduce, and a
#  toolchain that drifts silently is a toolchain that breaks silently.
#
#  Usage:
#    bash scripts/install-tools.sh          # install / upgrade to the pins
#    FORCE=1 bash scripts/install-tools.sh  # reinstall everything
# =============================================================================
set -euo pipefail

# --- pinned versions (verified against upstream releases) --------------------
KUBECTL_VERSION="v1.36.4"        # matches the k3s minor we run
HELM_VERSION="v4.2.4"
K3D_VERSION="v5.9.0"
TERRAFORM_VERSION="1.16.1"
K6_VERSION="v2.2.0"
COSIGN_VERSION="v3.1.3"
SYFT_VERSION="v1.51.1"
TRIVY_VERSION="0.74.0"
SOPS_VERSION="v3.13.3"
YQ_VERSION="v4.53.6"
ARGOCD_VERSION="v3.5.2"
KUSTOMIZE_VERSION="v5.8.1"

BIN=/usr/local/bin
FORCE="${FORCE:-0}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

GREEN='\033[32m'; DIM='\033[90m'; CYA='\033[36m'; YEL='\033[33m'; RST='\033[0m'
ok()   { printf "  ${GREEN}%-9s${RST} %s\n" "installed" "$*"; }
skip() { printf "  ${DIM}%-9s${RST} %s\n" "current" "$*"; }
upg()  { printf "  ${YEL}%-9s${RST} %s\n" "upgraded" "$*"; }
step() { printf "\n${CYA}==>${RST} %s\n" "$*"; }

# semver-ish extraction from arbitrary version output
curver() { "$@" 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1; }

# needs <bin> <wanted> <cmd...>  -> 0 when an install is required
needs() {
  local bin="$1" want="${2#v}"; shift 2
  [ "$FORCE" = "1" ] && return 0
  command -v "$bin" >/dev/null 2>&1 || return 0
  local cur; cur="$(curver "$@")"
  [ "$cur" = "$want" ] && return 1
  WAS="$cur"
  return 0
}

report() {  # report <bin> <want>
  if [ -n "${WAS:-}" ]; then upg "$1 ${WAS} -> ${2#v}"; WAS=""; else ok "$1 ${2#v}"; fi
}

step "Toolchain -> $BIN"

# --- kubectl -----------------------------------------------------------------
if needs kubectl "$KUBECTL_VERSION" kubectl version --client -o yaml; then
  curl -fsSLo "$TMP/kubectl" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  sudo install -m 0755 "$TMP/kubectl" "$BIN/kubectl"; report kubectl "$KUBECTL_VERSION"
else skip "kubectl ${KUBECTL_VERSION#v}"; fi

# --- helm --------------------------------------------------------------------
if needs helm "$HELM_VERSION" helm version --template '{{.Version}}'; then
  curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/linux-amd64/helm" "$BIN/helm"; report helm "$HELM_VERSION"
else skip "helm ${HELM_VERSION#v}"; fi

# --- k3d ---------------------------------------------------------------------
if needs k3d "$K3D_VERSION" k3d version; then
  curl -fsSL "https://github.com/k3d-io/k3d/releases/download/${K3D_VERSION}/k3d-linux-amd64" -o "$TMP/k3d"
  sudo install -m 0755 "$TMP/k3d" "$BIN/k3d"; report k3d "$K3D_VERSION"
else skip "k3d ${K3D_VERSION#v}"; fi

# --- terraform ---------------------------------------------------------------
if needs terraform "$TERRAFORM_VERSION" terraform version; then
  curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o "$TMP/tf.zip"
  unzip -q -o "$TMP/tf.zip" -d "$TMP"
  sudo install -m 0755 "$TMP/terraform" "$BIN/terraform"; report terraform "$TERRAFORM_VERSION"
else skip "terraform ${TERRAFORM_VERSION}"; fi

# --- k6 ----------------------------------------------------------------------
if needs k6 "$K6_VERSION" k6 version; then
  curl -fsSL "https://github.com/grafana/k6/releases/download/${K6_VERSION}/k6-${K6_VERSION}-linux-amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/k6-${K6_VERSION}-linux-amd64/k6" "$BIN/k6"; report k6 "$K6_VERSION"
else skip "k6 ${K6_VERSION#v}"; fi

# --- cosign ------------------------------------------------------------------
if needs cosign "$COSIGN_VERSION" cosign version; then
  curl -fsSL "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64" -o "$TMP/cosign"
  sudo install -m 0755 "$TMP/cosign" "$BIN/cosign"; report cosign "$COSIGN_VERSION"
else skip "cosign ${COSIGN_VERSION#v}"; fi

# --- syft --------------------------------------------------------------------
if needs syft "$SYFT_VERSION" syft version; then
  curl -fsSL "https://github.com/anchore/syft/releases/download/${SYFT_VERSION}/syft_${SYFT_VERSION#v}_linux_amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/syft" "$BIN/syft"; report syft "$SYFT_VERSION"
else skip "syft ${SYFT_VERSION#v}"; fi

# --- trivy -------------------------------------------------------------------
if needs trivy "$TRIVY_VERSION" trivy --version; then
  curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/trivy" "$BIN/trivy"; report trivy "$TRIVY_VERSION"
else skip "trivy ${TRIVY_VERSION}"; fi

# --- sops --------------------------------------------------------------------
if needs sops "$SOPS_VERSION" sops --version; then
  curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64" -o "$TMP/sops"
  sudo install -m 0755 "$TMP/sops" "$BIN/sops"; report sops "$SOPS_VERSION"
else skip "sops ${SOPS_VERSION#v}"; fi

# --- yq ----------------------------------------------------------------------
if needs yq "$YQ_VERSION" yq --version; then
  curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" -o "$TMP/yq"
  sudo install -m 0755 "$TMP/yq" "$BIN/yq"; report yq "$YQ_VERSION"
else skip "yq ${YQ_VERSION#v}"; fi

# --- argocd CLI --------------------------------------------------------------
if needs argocd "$ARGOCD_VERSION" argocd version --client --short; then
  curl -fsSL "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64" -o "$TMP/argocd"
  sudo install -m 0755 "$TMP/argocd" "$BIN/argocd"; report argocd "$ARGOCD_VERSION"
else skip "argocd ${ARGOCD_VERSION#v}"; fi

# --- kustomize ---------------------------------------------------------------
if needs kustomize "$KUSTOMIZE_VERSION" kustomize version; then
  curl -fsSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/kustomize" "$BIN/kustomize"; report kustomize "$KUSTOMIZE_VERSION"
else skip "kustomize ${KUSTOMIZE_VERSION#v}"; fi

# --- AWS CLI v2 (needed from M2 onwards) -------------------------------------
# NOTE: `command -v aws` is not sufficient here. With WSL interop enabled the
# Windows aws.exe shim appears on PATH but cannot execute under Linux, so we
# test for a native binary at an explicit path instead.
if [ ! -x "$BIN/aws" ] || [ "$FORCE" = "1" ]; then
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "$TMP/awscli.zip"
  unzip -q -o "$TMP/awscli.zip" -d "$TMP"
  sudo "$TMP/aws/install" --update >/dev/null
  ok "aws-cli $("$BIN/aws" --version 2>&1 | awk '{print $1}' | cut -d/ -f2)"
else skip "aws-cli $("$BIN/aws" --version 2>&1 | awk '{print $1}' | cut -d/ -f2)"; fi

# --- python tooling ----------------------------------------------------------
step "Python tooling"
pipx ensurepath >/dev/null 2>&1 || true
export PATH="$HOME/.local/bin:$PATH"
for pkg in pre-commit ruff; do
  if ! command -v "$pkg" >/dev/null 2>&1; then
    pipx install "$pkg" >/dev/null 2>&1 && ok "$pkg" || echo "  could not install $pkg"
  else
    skip "$pkg"
  fi
done

# --- shell niceties ----------------------------------------------------------
step "Shell completions"
mkdir -p "$HOME/.bash_completion.d"
kubectl completion bash > "$HOME/.bash_completion.d/kubectl" 2>/dev/null || true
helm    completion bash > "$HOME/.bash_completion.d/helm"    2>/dev/null || true
k3d     completion bash > "$HOME/.bash_completion.d/k3d"     2>/dev/null || true
if ! grep -q 'bash_completion.d' "$HOME/.bashrc" 2>/dev/null; then
  cat >> "$HOME/.bashrc" <<'RC'

# --- Palisade dev environment ---
export PATH="$HOME/.local/bin:$PATH"
for f in "$HOME"/.bash_completion.d/*; do [ -r "$f" ] && . "$f"; done
alias k=kubectl
complete -o default -F __start_kubectl k 2>/dev/null || true
RC
fi
ok "completions + aliases in ~/.bashrc"

printf "\n${GREEN}Toolchain ready.${RST} Next: ${CYA}make doctor${RST}\n\n"
