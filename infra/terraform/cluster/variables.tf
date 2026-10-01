variable "kubeconfig_path" {
  description = "Path to the kubeconfig that reaches the local k3d cluster"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubectl context name for the k3d cluster - see Makefile's CLUSTER/CTX"
  type        = string
  default     = "k3d-palisade"
}

variable "argocd_chart_version" {
  description = "argo-cd Helm chart version, verified against the live argo-helm releases before pinning"
  type        = string
  default     = "10.9.4"
}

variable "kyverno_chart_version" {
  description = <<-EOT
    kyverno Helm chart version, verified against the live kyverno.github.io/kyverno
    index before pinning. Deliberately held at 3.8.2 (app v1.18.2), one release behind
    the chart repo's latest (3.9.1, app v1.19.1) - see ADR 0018. v1.19.0 and v1.19.1
    both carry a confirmed upstream regression (kyverno/kyverno#17363) where
    verifyImages reports "no signatures found" against images that are, in fact,
    validly signed; the fix is tracked for v1.19.2, not yet released as of this pin.
    Re-verify against the kyverno.github.io/kyverno index before bumping past 3.9.1.
  EOT
  type        = string
  default     = "3.8.2"
}
