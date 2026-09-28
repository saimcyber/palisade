variable "aws_region" {
  description = "AWS region for every Palisade resource"
  type        = string
  default     = "us-east-1"
}

variable "app_bucket_name" {
  description = "Model-artifact bucket. Must match bootstrap's app_bucket_name - that's what ci_plan/ci_apply's IAM policies are scoped to."
  type        = string
  default     = "palisade-model-artifacts-316899784254"
}
