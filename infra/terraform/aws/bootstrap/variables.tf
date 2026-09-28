variable "aws_region" {
  description = "AWS region for every Palisade resource"
  type        = string
  default     = "us-east-1"
}

variable "github_repo" {
  description = "GitHub \"owner/repo\" this identity trusts - nothing else can assume these roles"
  type        = string
  default     = "saimcyber/palisade"
}

variable "state_bucket_name" {
  description = "S3 bucket that holds every Terraform root's remote state"
  type        = string
  default     = "palisade-tfstate-316899784254"
}

variable "app_bucket_name" {
  description = "S3 bucket for model artifacts, managed by the CI-applied aws/app root. Named here too because ci_apply's policy has to reference its ARN before that root has ever run."
  type        = string
  default     = "palisade-model-artifacts-316899784254"
}
