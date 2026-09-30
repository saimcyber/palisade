output "argocd_namespace" {
  value = helm_release.argocd.namespace
}

output "kyverno_namespace" {
  value = helm_release.kyverno.namespace
}
