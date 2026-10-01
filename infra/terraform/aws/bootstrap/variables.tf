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

variable "github_oidc_subject_prefix" {
  description = <<-EOT
    GitHub's immutable OIDC subject-claim prefix: "owner@owner_id/repo@repo_id".
    Newer repositories default to this format instead of
    the mutable "owner/repo" one, specifically so a renamed or recreated
    repo can't inherit an old trust policy's identity. Confirmed for this
    repo (new enough to be on the new default) by two independent
    checks: `gh api repos/saimcyber/palisade/actions/oidc/customization/sub`
    (use_immutable_subject: true, sub_claim_prefix given directly) and a
    CloudTrail AssumeRoleWithWebIdentity record from a real, deliberately
    run probe - the previous "owner/repo"-only trust policy was denied with
    exactly this discrepancy, which is how it was caught. See docs/adr/0009.
  EOT
  type        = string
  default     = "saimcyber@175656207/palisade@1359541168"
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
