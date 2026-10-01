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
  description = "kyverno Helm chart version, verified against the live kyverno.github.io/kyverno index before pinning"
  type        = string
  default     = "3.9.1"
}
