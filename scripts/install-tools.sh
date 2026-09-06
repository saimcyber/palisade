#!/usr/bin/env bash
# =============================================================================
#  Palisade - toolchain installer
#
#  Idempotent: safe to re-run. Installs pinned versions of every binary the
#  project needs into /usr/local/bin. Pinning matters here for the same reason
#  it matters in CI - "latest" is not a version you can reproduce later.
# =============================================================================
set -euo pipefail

# --- pinned versions ---------------------------------------------------------
K3D_VERSION="5.8.3"
KUBECTL_VERSION="v1.31.5"
HELM_VERSION="v3.16.4"
TERRAFORM_VERSION="1.10.5"
K6_VERSION="v0.55.0"
COSIGN_VERSION="v2.4.1"
SYFT_VERSION="v1.18.1"
TRIVY_VERSION="0.58.2"
SOPS_VERSION="v3.9.2"
YQ_VERSION="v4.44.6"
ARGOCD_VERSION="v2.13.3"
KUSTOMIZE_VERSION="v5.5.0"

BIN=/usr/local/bin
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ok()   { printf '  \033[32mok\033[0m      %s\n' "$*"; }
skip() { printf '  \033[90mpresent\033[0m %s\n' "$*"; }
step() { printf '\n\033[36m==>\033[0m %s\n' "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Compare "want" against the version string a binary reports; install if absent.
need() {
  local bin="$1"
  if have "$bin"; then
    return 1
  fi
  return 0
}

step "Installing DevOps toolchain into $BIN"

# --- kubectl -----------------------------------------------------------------
if need kubectl; then
  curl -fsSLo "$TMP/kubectl" "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
  sudo install -m 0755 "$TMP/kubectl" "$BIN/kubectl"
  ok "kubectl ${KUBECTL_VERSION}"
else skip "kubectl $(kubectl version --client -o json 2>/dev/null | jq -r .clientVersion.gitVersion 2>/dev/null || echo)"; fi

# --- helm --------------------------------------------------------------------
if need helm; then
  curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/linux-amd64/helm" "$BIN/helm"
  ok "helm ${HELM_VERSION}"
else skip "helm $(helm version --template '{{.Version}}' 2>/dev/null)"; fi

# --- k3d ---------------------------------------------------------------------
if need k3d; then
  curl -fsSL "https://github.com/k3d-io/k3d/releases/download/v${K3D_VERSION}/k3d-linux-amd64" -o "$TMP/k3d"
  sudo install -m 0755 "$TMP/k3d" "$BIN/k3d"
  ok "k3d ${K3D_VERSION}"
else skip "k3d $(k3d version | head -1 | awk '{print $3}')"; fi

# --- terraform ---------------------------------------------------------------
if need terraform; then
  curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o "$TMP/tf.zip"
  unzip -q -o "$TMP/tf.zip" -d "$TMP"
  sudo install -m 0755 "$TMP/terraform" "$BIN/terraform"
  ok "terraform ${TERRAFORM_VERSION}"
else skip "terraform $(terraform version -json 2>/dev/null | jq -r .terraform_version 2>/dev/null || echo)"; fi

# --- k6 ----------------------------------------------------------------------
if need k6; then
  curl -fsSL "https://github.com/grafana/k6/releases/download/${K6_VERSION}/k6-${K6_VERSION}-linux-amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/k6-${K6_VERSION}-linux-amd64/k6" "$BIN/k6"
  ok "k6 ${K6_VERSION}"
else skip "k6 $(k6 version | awk '{print $2}')"; fi

# --- cosign ------------------------------------------------------------------
if need cosign; then
  curl -fsSL "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64" -o "$TMP/cosign"
  sudo install -m 0755 "$TMP/cosign" "$BIN/cosign"
  ok "cosign ${COSIGN_VERSION}"
else skip "cosign $(cosign version 2>/dev/null | awk '/GitVersion/{print $2}')"; fi

# --- syft --------------------------------------------------------------------
if need syft; then
  curl -fsSL "https://github.com/anchore/syft/releases/download/${SYFT_VERSION}/syft_${SYFT_VERSION#v}_linux_amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/syft" "$BIN/syft"
  ok "syft ${SYFT_VERSION}"
else skip "syft $(syft version 2>/dev/null | awk '/Version:/{print $2}')"; fi

# --- trivy -------------------------------------------------------------------
if need trivy; then
  curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/trivy" "$BIN/trivy"
  ok "trivy ${TRIVY_VERSION}"
else skip "trivy $(trivy --version 2>/dev/null | head -1 | awk '{print $2}')"; fi

# --- sops --------------------------------------------------------------------
if need sops; then
  curl -fsSL "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64" -o "$TMP/sops"
  sudo install -m 0755 "$TMP/sops" "$BIN/sops"
  ok "sops ${SOPS_VERSION}"
else skip "sops $(sops --version 2>/dev/null | head -1 | awk '{print $2}')"; fi

# --- yq ----------------------------------------------------------------------
if need yq; then
  curl -fsSL "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" -o "$TMP/yq"
  sudo install -m 0755 "$TMP/yq" "$BIN/yq"
  ok "yq ${YQ_VERSION}"
else skip "yq $(yq --version | awk '{print $NF}')"; fi

# --- argocd CLI --------------------------------------------------------------
if need argocd; then
  curl -fsSL "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64" -o "$TMP/argocd"
  sudo install -m 0755 "$TMP/argocd" "$BIN/argocd"
  ok "argocd ${ARGOCD_VERSION}"
else skip "argocd $(argocd version --client --short 2>/dev/null | awk '{print $2}')"; fi

# --- kustomize ---------------------------------------------------------------
if need kustomize; then
  curl -fsSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_amd64.tar.gz" | tar -xz -C "$TMP"
  sudo install -m 0755 "$TMP/kustomize" "$BIN/kustomize"
  ok "kustomize ${KUSTOMIZE_VERSION}"
else skip "kustomize present"; fi

# --- AWS CLI v2 (needed from M2 onwards) -------------------------------------
if need aws; then
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "$TMP/awscli.zip"
  unzip -q -o "$TMP/awscli.zip" -d "$TMP"
  sudo "$TMP/aws/install" --update >/dev/null
  ok "aws-cli v2"
else skip "aws $(aws --version 2>&1 | awk '{print $1}')"; fi

# --- python tooling ----------------------------------------------------------
step "Python tooling"
pipx ensurepath >/dev/null 2>&1 || true
export PATH="$HOME/.local/bin:$PATH"
for pkg in pre-commit ruff; do
  if ! have "$pkg"; then
    pipx install "$pkg" >/dev/null 2>&1 && ok "$pkg" || echo "  could not install $pkg"
  else
    skip "$pkg"
  fi
done

# --- shell completions -------------------------------------------------------
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
ok "completions + aliases written to ~/.bashrc"

printf '\n\033[32mToolchain install complete.\033[0m Run: make doctor\n\n'
