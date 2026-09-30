# Palisade - cluster add-ons (Argo CD, Kyverno), applied by hand against
# the local k3d cluster - see ADR 0016. Never applied by CI: this cluster
# only exists on this laptop, and Terraform's own AWS identity split
# (docs/adr/0009) has nothing to do with local infra like this.
terraform {
  required_version = "~> 1.16"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.3"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
  }
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}
