output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github_actions.arn
}

output "ci_plan_role_arn" {
  value = aws_iam_role.ci_plan.arn
}

output "ci_apply_role_arn" {
  value = aws_iam_role.ci_apply.arn
}

output "state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}
