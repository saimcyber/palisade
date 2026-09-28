# 9. Terraform state bootstrap and identity split

- **Status:** Accepted

## Context

Two related chicken-and-egg problems come up starting M2:

1. Terraform's own state needs somewhere durable to live, but the S3 bucket
   meant to hold it doesn't exist until some Terraform apply creates it.
2. GitHub Actions needs an AWS identity to run Terraform at all, but that
   identity (the OIDC provider and its IAM roles) is itself infrastructure -
   something has to create it before CI can create anything else.

Both have the same shape: the thing granting access can't be the first thing
created by the access it grants.

## Decision

**Local state first, migrated into S3 once it exists.** The `bootstrap` root
(`infra/terraform/aws/bootstrap/`) starts with no `backend` block at all -
plain local state - and creates its own S3 bucket among its first resources.
Once that bucket exists, a `backend "s3" {}` block is added and
`terraform init -migrate-state` moves the local state into the bucket the
same config just created. This was verified directly: `terraform state list`
against the S3 backend shows every resource, and a subsequent `terraform
plan` from that backend shows zero drift.

**S3-native locking, not a DynamoDB table.** The backend uses
`use_lockfile = true`, generally available since Terraform 1.11 (well below
the 1.16.x pinned here). A lock table is one more always-on resource for a
project that promised never to provision anything beyond free-tier storage
and IAM - `use_lockfile` gets the same safety without it.

**Identity lives in a separate root, applied only by hand.** `bootstrap`
creates the GitHub OIDC provider and two IAM roles (`palisade-ci-plan`,
`palisade-ci-apply`) and is never applied by CI - only from a developer
machine with the `palisade` AWS profile. A second root,
`infra/terraform/aws/app/`, holds only the model-artifact S3 bucket, and is
what CI actually plans and applies. `app/` deliberately contains no
`aws_iam_*` resource of any kind - checked by reading its plan output, which
shows only S3 resources.

**Two roles, not one, and neither with CI-editable permissions beyond one S3
bucket.** `palisade-ci-plan`'s trust policy only matches the OIDC `sub` claim
GitHub issues for a pull-request run (`repo:saimcyber/palisade:pull_request`);
`palisade-ci-apply` only matches a push to `main`
(`repo:saimcyber/palisade:ref:refs/heads/main`). A single role assumable from
both would let any open PR - reviewed or not - mutate real infrastructure,
which is exactly what gating `apply` on merge is supposed to prevent. Each
role's only permission policy is scoped to the single `app` bucket's ARN
(`ci_plan` read-only, `ci_apply` full bucket lifecycle) - neither can touch
IAM, so neither can grant itself more than this.

**The GitHub OIDC thumbprint is fetched, not hand-typed.** AWS has validated
this specific provider's TLS certificate against its own trusted CA library
since 2023, not against the configured thumbprint - true for GitHub, GitLab,
Auth0 and Google's OIDC endpoints specifically. Terraform's
`aws_iam_openid_connect_provider` resource still requires a non-empty
`thumbprint_list` argument regardless, so it's populated from a live
`tls_certificate` data source pointed at the endpoint rather than a
copy-pasted value nobody would remember to keep current.

## Consequences

- Every piece of this project's AWS trust boundary is code, reviewable in a
  PR, not a `console.aws.amazon.com` click-through nobody wrote down -
  including the bucket every other root's state depends on.
- `bootstrap/` is a manual step outside the CI pipeline's blast radius by
  design. Anyone extending this project has to consciously choose to apply
  it by hand; there's no path where a CI run modifies IAM.
- `app/`'s statement of intent is enforceable, not just documented: its own
  `terraform plan` output is the proof that it never touches IAM, every time
  it runs.
