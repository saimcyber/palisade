#!/usr/bin/env bash
# =============================================================================
#  Palisade - the billing guard, run before any Terraform exists
#
#  WHY THIS EXISTS
#  ----------------
#  M2's cost-control rule is explicit: set a billing alarm before writing a
#  single line of Terraform. That ordering only holds if the guard is created
#  by something other than the Terraform this milestone is about to write -
#  otherwise it would be stood up by the same apply as the infrastructure it's
#  meant to backstop, which defeats the point. So this is a one-time,
#  hand-run, idempotent CLI script instead of a Terraform resource.
#
#  AWS Budgets over a classic CloudWatch billing alarm: Budgets doesn't need
#  the "Receive Billing Alerts" account-root preference toggle that classic
#  billing alarms require (a toggle only the root user can flip, only from
#  us-east-1), so it works immediately against a plain IAM user.
#
#  Safe to re-run: checks for the budget by name before creating it.
# =============================================================================
set -euo pipefail

PROFILE="${AWS_PROFILE:-palisade}"
BUDGET_NAME="${BUDGET_NAME:-palisade-monthly-guard}"
LIMIT_USD="${LIMIT_USD:-5}"
NOTIFY_EMAIL="${NOTIFY_EMAIL:-saimzaib69@gmail.com}"

GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'
ok()   { printf '  %bok%b   %s\n' "$GREEN" "$RST" "$*"; }
note() { printf '  %bnote%b %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %bfail%b %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n%b==>%b %s\n' "$CYA" "$RST" "$*"; }

command -v aws >/dev/null || die "aws CLI not found"

step "Resolving account"
ACCOUNT_ID="$(aws sts get-caller-identity --profile "$PROFILE" --query Account --output text)" \
  || die "aws sts get-caller-identity failed for profile '$PROFILE' - fix credentials first"
ok "account $ACCOUNT_ID (profile $PROFILE)"

step "Checking for an existing budget named '$BUDGET_NAME'"
if aws budgets describe-budget \
     --account-id "$ACCOUNT_ID" \
     --budget-name "$BUDGET_NAME" \
     --profile "$PROFILE" >/dev/null 2>&1; then
  ok "budget already exists - nothing to do"
  exit 0
fi
note "not found - creating it"

TMP_BUDGET="$(mktemp)"
TMP_NOTIFY="$(mktemp)"
trap 'rm -f "$TMP_BUDGET" "$TMP_NOTIFY"' EXIT

cat > "$TMP_BUDGET" <<JSON
{
  "BudgetName": "$BUDGET_NAME",
  "BudgetLimit": { "Amount": "$LIMIT_USD", "Unit": "USD" },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
JSON

cat > "$TMP_NOTIFY" <<JSON
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      { "SubscriptionType": "EMAIL", "Address": "$NOTIFY_EMAIL" }
    ]
  },
  {
    "Notification": {
      "NotificationType": "FORECASTED",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      { "SubscriptionType": "EMAIL", "Address": "$NOTIFY_EMAIL" }
    ]
  }
]
JSON

step "Creating budget '$BUDGET_NAME' (\$$LIMIT_USD/month, alerts to $NOTIFY_EMAIL)"
aws budgets create-budget \
  --account-id "$ACCOUNT_ID" \
  --budget file://"$TMP_BUDGET" \
  --notifications-with-subscribers file://"$TMP_NOTIFY" \
  --profile "$PROFILE"
ok "created"

step "Verifying"
aws budgets describe-budget \
  --account-id "$ACCOUNT_ID" \
  --budget-name "$BUDGET_NAME" \
  --profile "$PROFILE" \
  --query 'Budget.{Name:BudgetName,Limit:BudgetLimit.Amount,Unit:BudgetLimit.Unit}' \
  --output table
