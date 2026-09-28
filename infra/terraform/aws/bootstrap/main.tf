data "aws_caller_identity" "current" {}

# AWS validates the GitHub OIDC endpoint against its own trusted CA library,
# not against this thumbprint - true for GitHub specifically since 2023-07
# (verified against the current terraform-provider-aws docs and open issues
# while building this). thumbprint_list is still a mandatory argument on the
# resource, so it's fetched dynamically rather than hand-typed, which keeps
# it correct without anyone having to remember to update a magic string.
data "tls_certificate" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_actions.certificates[0].sha1_fingerprint]
}

# --- trust policies: two roles, not one -------------------------------------
#
# ci_plan is assumable from a pull_request run; ci_apply only from a push to
# main. A single role assumable from both would let any PR - including ones
# nobody has reviewed yet - mutate real infrastructure, which defeats the
# entire point of gating `apply` on merge. See docs/adr/0009.

data "aws_iam_policy_document" "ci_plan_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:pull_request"]
    }
  }
}

data "aws_iam_policy_document" "ci_apply_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "ci_plan" {
  name                 = "palisade-ci-plan"
  assume_role_policy   = data.aws_iam_policy_document.ci_plan_trust.json
  max_session_duration = 3600
}

resource "aws_iam_role" "ci_apply" {
  name                 = "palisade-ci-apply"
  assume_role_policy   = data.aws_iam_policy_document.ci_apply_trust.json
  max_session_duration = 3600
}

# Neither role has any permission policy yet - AssumeRoleWithWebIdentity plus
# sts:GetCallerIdentity needs none, which is what the first probe workflow
# proves (task 4). Their scoped S3-only policies are attached below, once the
# app bucket's ARN is known - naming it here (variables.tf) rather than
# waiting for the aws/app root to create it, since IAM has to exist before
# anything can be granted access to it.

data "aws_iam_policy_document" "app_bucket_plan" {
  statement {
    sid    = "ReadOnlyOnAppBucket"
    effect = "Allow"
    actions = [
      "s3:GetBucket*",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetEncryptionConfiguration",
      "s3:GetBucketPolicy",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketVersioning",
    ]
    resources = [
      "arn:aws:s3:::${var.app_bucket_name}",
      "arn:aws:s3:::${var.app_bucket_name}/*",
    ]
  }
}

data "aws_iam_policy_document" "app_bucket_apply" {
  statement {
    sid    = "ManageAppBucket"
    effect = "Allow"
    actions = [
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:GetBucket*",
      "s3:ListBucket",
      "s3:PutBucketVersioning",
      "s3:PutEncryptionConfiguration",
      "s3:GetEncryptionConfiguration",
      "s3:PutBucketPublicAccessBlock",
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPolicy",
      "s3:GetBucketPolicy",
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:aws:s3:::${var.app_bucket_name}",
      "arn:aws:s3:::${var.app_bucket_name}/*",
    ]
  }
}

resource "aws_iam_role_policy" "ci_plan_app_bucket" {
  name   = "app-bucket-read-only"
  role   = aws_iam_role.ci_plan.id
  policy = data.aws_iam_policy_document.app_bucket_plan.json
}

resource "aws_iam_role_policy" "ci_apply_app_bucket" {
  name   = "app-bucket-manage"
  role   = aws_iam_role.ci_apply.id
  policy = data.aws_iam_policy_document.app_bucket_apply.json
}

# --- Terraform state bucket --------------------------------------------------
#
# Bootstrapped with local state on first apply, then migrated into this same
# bucket (`terraform init -migrate-state`) once it exists. S3-native object
# locking (use_lockfile in the backend block, added after migration) replaces
# a DynamoDB lock table - GA since Terraform 1.11, no extra always-on
# resource for a project that promised never to provision compute.

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
