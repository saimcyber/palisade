# Palisade - the CI-applied Terraform root
#
# Owns exactly one thing: the model-artifact S3 bucket. Deliberately does not
# and must not define any aws_iam_* or aws_iam_openid_connect_provider
# resource - those live only in ../bootstrap, applied by hand. A role that
# can apply here could, if this root also managed IAM, grant itself more
# IAM - see docs/adr/0009. GitHub Actions applies this root through
# palisade-ci-apply (push to main) / plans it through palisade-ci-plan (PR),
# both created by the bootstrap root.

terraform {
  required_version = "~> 1.16"

  backend "s3" {
    bucket       = "palisade-tfstate-316899784254"
    key          = "app/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.66"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
