# Palisade - Terraform bootstrap root
#
# Creates the identity this whole project trusts: the GitHub OIDC provider,
# the two IAM roles GitHub Actions assumes, and the S3 bucket that holds
# every Terraform root's remote state - including this root's own.
#
# Applied ONLY by hand, never by CI (see docs/adr/0009). A CI role that could
# also edit IAM could grant itself more IAM, which defeats the point of a
# scoped, auditable identity in the first place.
#
# Chicken-and-egg note: this file intentionally has NO `backend` block on
# first apply, because the S3 bucket the backend would point at doesn't
# exist until this same config creates it. Once it exists, a `backend "s3"`
# block is added and `terraform init -migrate-state` moves this root's state
# into the bucket it just created. See docs/adr/0009 for the full reasoning.

terraform {
  required_version = "~> 1.16"

  backend "s3" {
    bucket       = "palisade-tfstate-316899784254"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.66"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
