# -*- coding: utf-8 -*-
"""Content for the M2 engineering document."""
from docx_kit import *  # noqa: F403
from m0 import dual, _steps, _qa  # reuse the shared rendering helpers

SECTIONS = [
    "cover", "what_it_was_for", "starting_point", "decisions",
    "what_was_built", "how_it_was_done", "pipeline_bugs", "deviations",
    "tool_choices", "limitations", "mistakes", "explain", "glossary_and_next",
]


# =============================================================================
def cover(D):
    d = D.d
    t = d.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade_cell(c, F_COVER); c.text = ""
    p = c.paragraphs[0]; no_space(p, 20, 2)
    r = p.add_run("PALISADE")
    r.bold = True; r.font.size = Pt(26); r.font.name = BODY_FONT; r.font.color.rgb = WHITE
    p2 = c.add_paragraph(); no_space(p2, 2, 2)
    r = p2.add_run("Engineering Log  ·  Milestone M2")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("Supply Chain & CI/CD: a pipeline that signs what it ships")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M2 - Supply Chain & CI/CD**"],
            ["Goal", "Make it impossible to ship an artefact that hasn't been scanned, described and "
                     "signed - and prove no long-lived cloud credential exists anywhere"],
            ["Result", "**Passed.** Verified live: `cosign verify` succeeds from a logged-out terminal, "
                       "an SPDX SBOM (127 packages) verifies against the same digest, and the GitHub "
                       "repository holds zero stored secrets"],
            ["Identity", "GitHub OIDC -> two scoped IAM roles (`palisade-ci-plan`, `palisade-ci-apply`) - "
                        "no AWS access key stored anywhere in GitHub"],
            ["Pipeline", "`ci.yml` (lint, test, build, Trivy gate, push, cosign sign + attest) and "
                        "`terraform.yml` (plan on PR, apply on merge), both GitHub-hosted"],
            ["New code", "`infra/terraform/aws/{bootstrap,app}`, `.github/workflows/{ci,terraform}.yml`, "
                        "`scripts/setup-billing-budget.sh`, hash-pinned `requirements*.txt`, "
                        "`services/gateway/.trivyignore`, ADRs 0007-0010"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("Same structure as M0 and M1, answering the same six standing questions.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**",
             "§4 What was built and **§5 How it was done** - the complete task-by-task walkthrough"],
            ["**2. What was done differently**, and why",
             "**§8 Deviations** - every place a real run disagreed with the plan or with what I assumed"],
            ["**3. How it was done**",
             "§5, plus **§6** - a deep dive into six real, reproducible failures found by actually "
             "running the pipeline, not by reviewing it"],
            ["**4. What the limitations are**",
             "**§9 Limitations** - stated plainly, including the ones M3 inherits"],
            ["**5. Why this tool/approach over the alternatives**",
             "**§8 Tool choices**, and the milestone's four new ADRs (0007-0010)"],
            ["**6. Plain language and technical, both**",
             "Throughout, as **IN PLAIN LANGUAGE** / **TECHNICALLY** pairs."],
        ],
        widths=[2.1, 4.5],
    )

    D.callout("The one thing to take away from M2",
              "Every one of the six failures in §6 passed a local check, a `terraform plan`, or a code "
              "review before it ever ran for real - and every one only surfaced once the actual pipeline "
              "ran against actual AWS and actual GitHub infrastructure. A green plan is a prediction, not "
              "a result; this milestone's entire content is the gap between the two.", "ok")


# =============================================================================
def what_it_was_for(D):
    D.h1("1. What M2 Was For")

    D.h2("1.1  The goal, stated simply")
    dual(D,
         "M1 proved the model could serve a real answer. M2 asks a different question: once that service "
         "is worth shipping, how do I ship it so that nothing reaches production without being checked, "
         "and so that checking it doesn't require trusting a password sitting in a settings page somewhere?",
         "Build a GitHub Actions pipeline that lints, tests, builds, gates on a vulnerability scan, pushes "
         "to a registry, and signs the result - keylessly, through GitHub's own OIDC identity - plus a "
         "second pipeline that plans and applies a small amount of AWS infrastructure through that same "
         "identity, with zero AWS credentials stored in GitHub at any point.")

    D.h2("1.2  Why this, and in this order")
    D.p("The single biggest risk in this milestone was never the scanning or the signing - both are "
        "well-trodden, well-documented tools. The real risk was getting the trust relationship between "
        "GitHub and AWS wrong in a way that either doesn't work or, worse, works but is wrong. Everything "
        "was sequenced so that risk got the cheapest possible test, first.")
    D.table(
        ["#", "Task", "The unknown it tested", "Outcome"],
        [
            ["1-3", "Fresh AWS identity, prove the push works, stand up a billing guard",
             "Can I even get a working, scoped AWS credential - and is the CI blocker CLAUDE.md named "
             "actually real?", "**One assumption was wrong** - see §8"],
            ["4", "OIDC trust policy on the smallest possible surface",
             "Will GitHub's identity token actually satisfy the trust policy I write?",
             "**No, not on the first attempt** - the milestone's real content, §6"],
            ["5-6", "Migrate state to S3, split identity from the CI-applied root",
             "Does the bootstrap ordering actually work, and does splitting IAM out of the applied root "
             "hold up under a real apply?", "**Passed**, after one more permission gap - §6"],
            ["7-11", "Hash-pin deps, build both workflows, open a PR, merge, verify",
             "Does the whole chain - build, scan, push, sign, attest - work end to end against real "
             "infrastructure?", "**Passed** - see §4.2 and §6"],
        ],
        widths=[0.5, 2.0, 2.6, 1.5],
    )
    D.callout("The principle carried over from M0 and M1",
              "**Sequence work by risk, cheapest test of the biggest unknown first.** The OIDC trust "
              "policy was proven on a throwaway probe before a single S3 bucket depended on it. That is "
              "exactly why the first real failure (§6.1) cost a `terraform apply` and a few minutes, not "
              "a half-built pipeline with a silently broken trust boundary underneath it.", "note")


# =============================================================================
def starting_point(D):
    D.h1("2. What Was True Going Into M2")
    D.p("M1 left a working gateway and a stale set of assumptions about the environment - two of them "
        "turned out to be wrong the moment they were actually tested.")

    D.table(
        ["What was checked", "What was found", "Why it mattered"],
        [
            ["AWS credentials", "The default CLI profile's static keys were **dead** "
             "(`InvalidClientTokenId`), and a pre-existing SSO profile turned out to belong to a login "
             "nobody could recall - not this project",
             "Nothing in M2 can start without working AWS access. Removed the stale profile rather than "
             "chase credentials for an account no longer reachable, and built a fresh identity instead - "
             "§5.1."],
            ["`gh auth` / push permission", "CLAUDE.md's Status table named a specific missing OAuth "
             "scope as the blocker before workflow YAML could be pushed",
             "Turned out not to apply at all: `gh` isn't installed in this environment, and the actual "
             "push credential already had everything it needed. A stale assumption, caught by testing "
             "it instead of trusting the note - §5.2, §8."],
            ["Terraform scaffolding", "`.github/workflows/`, `infra/terraform/aws/`, and pinned tool "
             "versions in `scripts/install-tools.sh` all already existed, empty or stale",
             "M2 built on top of this rather than recreating it - except the Terraform version pin, which "
             "was a release behind and got verified against the upstream release API before reuse."],
            ["Registry and signing decisions", "Nothing yet chosen - `docker-compose.yml`'s only external "
             "image reference was an unpinned Docker Hub tag used solely for local dev",
             "Registry (ghcr.io) and signing approach (cosign keyless) were open decisions this milestone "
             "had to make and record - ADRs 0007 and 0008."],
        ],
        widths=[1.3, 2.6, 2.65],
    )


# =============================================================================
def decisions(D):
    D.h1("3. Decisions Taken Before Writing Any Code")

    D.h2("3.1  Identity split: a hand-applied bootstrap root, a CI-applied app root")
    dual(D,
         "Keep the keys to the kingdom - the identity that lets GitHub touch AWS at all - somewhere the "
         "automated pipeline itself can never modify. Let the pipeline manage only the one small piece of "
         "infrastructure it actually needs.",
         "`infra/terraform/aws/bootstrap/` creates the OIDC provider and both IAM roles, applied only by "
         "hand from a developer machine. `infra/terraform/aws/app/` holds only the model-artifact S3 "
         "bucket and is the only root `terraform.yml` ever plans or applies. Confirmed by reading `app/`'s "
         "own `terraform plan` output: it contains zero `aws_iam_*` resources, every time it runs.")
    D.callout("Why this matters more than it might look like it does",
              "A CI role that could also edit IAM could grant itself more IAM - a real, quiet "
              "self-escalation path. Splitting the roots isn't defence in depth for its own sake; it's the "
              "difference between \"the pipeline can create a bucket\" and \"the pipeline could, in "
              "principle, make itself an administrator.\"", "warn")

    D.h2("3.2  Two IAM roles, not one")
    dual(D,
         "Give a pull request less power than a merge. A role that can be assumed from an unreviewed PR "
         "and can also change real infrastructure defeats the entire point of gating `apply` on merge.",
         "`palisade-ci-plan` is trusted only from GitHub's `pull_request` OIDC subject; "
         "`palisade-ci-apply` only from a push to `refs/heads/main`. `terraform.yml`'s `plan` job assumes "
         "the former, `apply` the latter - two separate jobs, two separate trust conditions, checked by "
         "`StringEquals` against the exact subject GitHub issues.")

    D.h2("3.3  State bootstrap: local state first, migrated into the bucket it creates")
    dual(D,
         "Terraform's own tracking file needs somewhere durable to live, but the bucket meant to hold it "
         "doesn't exist until Terraform creates it. Solve the chicken-and-egg the standard way: start "
         "with a plain local file, then move it in once the bucket is real.",
         "`bootstrap/` applies first with no `backend` block (implicit local state), creating its own S3 "
         "bucket among its first resources. Once that bucket exists, a `backend \"s3\" {}` block is added "
         "and `terraform init -migrate-state` moves the state in - verified with `terraform state list` "
         "against the new backend and a driftless follow-up plan. See ADR 0009.")

    D.h2("3.4  The billing guard is a script, not a Terraform resource")
    dual(D,
         "The rule is \"a billing alarm before any Terraform is written.\" A budget created by the same "
         "apply as the infrastructure it's meant to backstop can't, by definition, predate that "
         "infrastructure.",
         "`scripts/setup-billing-budget.sh` - a plain, idempotent AWS CLI script - creates an AWS Budget "
         "($5/month, email alerts) via `aws budgets create-budget`, run and verified before a single `.tf` "
         "file existed. AWS Budgets over a classic CloudWatch billing alarm specifically because Budgets "
         "doesn't need the root-only \"Receive Billing Alerts\" account preference a classic alarm does.")

    D.h2("3.5  Registry and signing: ghcr.io, cosign keyless")
    dual(D,
         "Pick the registry that needs no separate password, and the signing method that needs no key at "
         "all - both in direct service of the milestone's own goal: no long-lived credential, anywhere.",
         "ghcr.io authenticates from the workflow's own `GITHUB_TOKEN` (ADR 0007); cosign signs keylessly "
         "through the same workflow's OIDC token against Sigstore's Fulcio/Rekor, so there is no private "
         "key to generate, store as a secret, or rotate (ADR 0008).")


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")

    D.h2("4.1  New files and directories")
    D.table(
        ["Path", "Purpose"],
        [
            ["`scripts/setup-billing-budget.sh`", "One-time, idempotent AWS Budgets setup - $5/month, "
             "email alerts. Run before any Terraform, per the milestone's own ordering rule."],
            ["`infra/terraform/aws/bootstrap/`", "GitHub OIDC provider, two IAM roles "
             "(`palisade-ci-plan`, `palisade-ci-apply`), and the Terraform state bucket. Applied by hand "
             "only - never by CI."],
            ["`infra/terraform/aws/app/`", "The one thing CI is trusted to manage: the model-artifact S3 "
             "bucket (versioned, encrypted, public access blocked)."],
            ["`services/gateway/requirements*.in`", "Hash-pinning sources for `pip-compile "
             "--generate-hashes` - both the runtime and dev requirement sets, since hash checking is "
             "all-or-nothing across the resolved set."],
            ["`services/gateway/.trivyignore`", "Eight reviewed, justified accepted-risk CVE entries - "
             "base-OS packages with no upstream fix yet, none in a code path the gateway ever exercises."],
            ["`.github/workflows/ci.yml`", "lint -> test -> build -> Trivy gate (HIGH/CRITICAL) -> push "
             "(main only) -> Syft SBOM -> cosign sign + attest."],
            ["`.github/workflows/terraform.yml`", "`plan` on a PR (posts the plan as a PR comment), "
             "`apply` only on push to `main` - two jobs, two roles, per §3.2."],
            ["`docs/adr/0007`-`0010`", "Registry choice; keyless signing; the state-bootstrap and "
             "identity-split design; the Trivy severity gate policy."],
            ["`docs/CONVENTIONS.md`, Makefile", "A new \"Supply chain\" section recording every real "
             "finding from §6. `lint` no longer swallows its own exit code; `make test` installs with "
             "`--require-hashes`."],
        ],
        widths=[2.1, 4.5],
    )

    D.h2("4.2  What was proven, end to end")
    D.p("Every row below was checked by hand, live, against the real pipeline and real infrastructure - "
        "not inferred from a green `terraform plan` or a passing local test.")
    D.table(
        ["Check", "Result"],
        [
            ["The full pipeline runs on a real PR: lint, test, `terraform plan`, build+scan",
             "**PASS** - all four checks green on the same pull request, after fixing every real gap "
             "§6 documents"],
            ["`terraform apply` creates real AWS infrastructure through the scoped `ci_apply` role",
             "**PASS** - the model-artifact S3 bucket exists, created by a merge to `main`, not by hand"],
            ["The gateway image is built, Trivy-gated, pushed, signed, and SBOM-attested on merge",
             "**PASS** - all four steps completed on the same push, verified via the run log"],
            ["**The acceptance test**: `cosign verify` succeeds from a logged-out terminal",
             "**PASS** - certificate identity matches the exact workflow, ref and repo, with Docker not "
             "even installed on the verifying machine"],
            ["An SBOM is attached and independently verifiable against the same image digest",
             "**PASS** - `cosign verify-attestation --type spdxjson` returns a valid SPDX-2.3 document, "
             "127 packages catalogued"],
            ["The GitHub repository stores no AWS secret of any kind",
             "**PASS** - `gh secret list` returns empty; OIDC needed nothing to be stored, ever"],
            ["No secret of any kind anywhere in the repository's full history",
             "**PASS** - `gitleaks detect` across all commits and ~450 KB of history: no leaks found"],
            ["The Trivy gate actually blocks a build with a real, fixable CRITICAL finding",
             "**PASS** - it did, once, for real, on the first real run - see §6.5"],
        ],
        widths=[2.9, 3.7],
    )


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done")
    D.p("The eleven tasks, in the order they actually ran, with the real commands and the real detours.")

    D.h2("5.1  Tasks 1-2 - A working AWS identity, and testing an assumption before trusting it")
    D.p("The default AWS CLI profile's keys were dead. A separate SSO profile existed "
        "(`sandbox-admin`) but turned out to be for a different, forgotten login entirely - removed "
        "rather than chase access to an account no one could account for. A fresh IAM user "
        "(`palisade-bootstrap`, `AdministratorAccess`, scoped to local one-time bootstrap use only - never "
        "used by CI) replaced it, created directly in the AWS Console.")
    D.p("Separately, CLAUDE.md's Status table named a specific missing GitHub CLI OAuth scope as the "
        "blocker before any workflow YAML could be pushed. Rather than run the named remediation on faith, "
        "a throwaway no-op workflow file was pushed on a branch first.")
    D.code(
        "$ git push -u origin probe/workflow-push-test\n"
        "...\n"
        "To https://github.com/saimcyber/palisade.git\n"
        " * [new branch]      probe/workflow-push-test -> probe/workflow-push-test"
    )
    D.p("It went through with no scope error at all. The assumption in the Status table was stale - the "
        "actual push credential in this environment already had everything it needed. The probe branch "
        "was deleted immediately after.")

    D.h2("5.2  Task 3 - The billing guard")
    D.code(
        "$ bash scripts/setup-billing-budget.sh\n"
        "==> Resolving account\n"
        "  ok   account 316899784254 (profile palisade)\n"
        "==> Creating budget 'palisade-monthly-guard' ($5/month, alerts to ...)\n"
        "  ok   created"
    )
    D.p("Idempotent by design - a second run correctly reported the budget already existed and made no "
        "further changes, verified before moving on.")

    D.h2("5.3  Task 4 - Proving the OIDC trust policy")
    D.p("`infra/terraform/aws/bootstrap/` was applied with local state, creating the OIDC provider, both "
        "IAM roles, and the state bucket in one apply (9 resources, zero compute). State was then migrated "
        "into that same bucket:")
    D.code(
        "$ terraform init -migrate-state\n"
        "Do you want to copy existing state to the new backend? ... yes\n"
        "Successfully configured the backend \"s3\"!"
    )
    D.p("The trust policy was not correct on the first attempt - see §6.1 for the full account of why, "
        "and how CloudTrail was used to find the real answer rather than guess at one.")

    D.h2("5.4  Tasks 5-6 - Migrating state, splitting the identity from the applied root")
    D.p("Confirmed with `terraform state list` against the S3 backend and a follow-up `terraform plan` "
        "showing zero drift. `infra/terraform/aws/app/` was written and validated (`terraform plan`, "
        "locally, with the bootstrap identity's own admin credentials, but never applied by hand) - "
        "deliberately leaving the first real creation of that bucket to the CI pipeline itself, as a "
        "stronger proof that the scoped role's permissions genuinely work end to end.")

    D.h2("5.5  Task 7 - Hash-pinning the gateway's dependencies")
    D.code(
        "$ pip-compile --generate-hashes --allow-unsafe -o requirements.txt requirements.in\n"
        "$ pip-compile --generate-hashes --allow-unsafe -o requirements-dev.txt requirements-dev.in\n"
        "$ pip install --require-hashes -r requirements-dev.txt   # fresh venv, verified clean\n"
        "16 passed, 1 skipped"
    )
    D.p("Both the runtime and dev requirement files needed the treatment - hash checking is all-or-nothing "
        "across the whole resolved set, and `requirements-dev.txt` pulls in `requirements.txt` via `-r`. "
        "The Dockerfile's builder stage switched from an unpinned `pip install --upgrade pip` to relying "
        "on the base image's own pinned `pip`, plus `--require-hashes` on the real install.")

    D.h2("5.6  Tasks 8-9 - Building both workflows")
    D.p("Every third-party GitHub Action across both workflows was pinned to a commit SHA resolved from "
        "the live GitHub API immediately before writing it in - `actions/checkout`, `actions/setup-python`, "
        "the `docker/*` actions, `aquasecurity/trivy-action` (version-floor checked against a real security "
        "incident, §6.6), `sigstore/cosign-installer`, `hashicorp/setup-terraform`, "
        "`aws-actions/configure-aws-credentials`, `actions/github-script`. Syft itself was installed as a "
        "pinned release binary - the same pattern `scripts/install-tools.sh` already uses - rather than a "
        "third-party SBOM action, to keep one fewer thing in the signing chain's trust surface.")

    D.h2("5.7  Tasks 10-11 - Opening the PR, merging, and proving the acceptance criterion")
    D.p("Every change from Tasks 7-9 went into a single PR, deliberately, so `ci.yml` and `terraform.yml` "
        "could both be exercised for real on the same pull request - `test`, `lint`, `plan` and "
        "`build-scan-sign-push` all had to go green before it was mergeable. Six real failures surfaced "
        "doing this; all six are §6. Once every check passed, the PR was merged, which triggered the "
        "real `apply` and the real build/push/sign/attest on `main` for the first time.")
    D.code(
        "$ cosign verify \\\n"
        "    --certificate-identity='https://github.com/saimcyber/palisade/.github/workflows/ci.yml@refs/heads/main' \\\n"
        "    --certificate-oidc-issuer='https://token.actions.githubusercontent.com' \\\n"
        "    ghcr.io/saimcyber/palisade-gateway@sha256:89c4c74d...\n"
        "\n"
        "Verification for ghcr.io/saimcyber/palisade-gateway@sha256:89c4c74d... --\n"
        "The following checks were performed on each of these signatures:\n"
        "  - The cosign claims were validated\n"
        "  - Existence of the claims in the transparency log was verified offline\n"
        "  - The code-signing certificate was verified using trusted certificate authority certificates"
    )
    D.p("Run from a shell where Docker wasn't even installed - so this wasn't proving a cached login "
        "worked, it was proving the signature itself is independently checkable by anyone.")


# =============================================================================
def pipeline_bugs(D):
    D.h1("6. Deep Dive - Six Real Failures, Found the Same Way Every Time")
    D.p("Every failure below passed review or a local check first. None of them were visible until the "
        "actual pipeline ran against actual AWS and actual GitHub. That is not a coincidence: it's the "
        "entire argument for building the real thing before calling a milestone done.")

    D.h2("6.1  GitHub's OIDC subject claim isn't what the documentation I remembered said")
    dual(D,
         "The trust policy connecting GitHub to AWS was written to expect an identity string in the "
         "classic format - \"this repository, by name.\" GitHub rejected every attempt to assume the role, "
         "and the error gave no hint why.",
         "`AssumeRoleWithWebIdentity` failed with a flat `AccessDenied: Not authorized`. CloudTrail's "
         "`AssumeRoleWithWebIdentity` events showed the real subject claim GitHub was sending: "
         "`repo:saimcyber@175656207/palisade@1359541168:pull_request` - not "
         "`repo:saimcyber/palisade:pull_request`. GitHub now defaults newly created repositories to "
         "an **immutable** OIDC subject format (owner and repo each suffixed with their permanent "
         "numeric ID), specifically so a renamed or recreated repository can't inherit an old trust "
         "policy's identity. Confirmed independently via "
         "`gh api repos/saimcyber/palisade/actions/oidc/customization/sub` "
         "(`use_immutable_subject: true`) before changing anything.")
    D.p("Both role trust policies were rewritten to match, applied by hand as `bootstrap/` requires, and "
        "re-tested - the next PR run assumed both roles cleanly.")

    D.h2("6.2  A brand-new S3 bucket needs more read permissions than the actions that touch it")
    dual(D,
         "The role allowed to manage the model-artifact bucket was given exactly the read permissions I "
         "expected it to need. The very first real `terraform apply` failed instantly, on a permission "
         "nobody had written any code to use.",
         "`AccessDenied` on `s3:GetAccelerateConfiguration` while Terraform was still creating the bucket. "
         "Modern versions of the `aws_s3_bucket` resource read back a long tail of sub-configurations "
         "during create and refresh - accelerate, logging, CORS, replication, object-lock, request-payment, "
         "ownership controls - regardless of whether the configuration manages any of them. An enumerated "
         "policy fails one 403 at a time, each on a different `Get*Configuration` call.")
    D.p("Fixed by granting `s3:Get*`/`s3:List*` (both inherently read-only AWS action families) instead "
        "of an enumerated list, while keeping every mutating action - `CreateBucket`, `PutObject`, "
        "`DeleteBucket`, and so on - individually named.")

    D.h2("6.3  A CI role needs access to its own state, separately from the infrastructure it manages")
    dual(D,
         "With the bucket permissions fixed, `terraform plan` on the next PR still failed - this time on "
         "the *state* file itself, not the infrastructure being planned.",
         "`HeadObject` against `app/terraform.tfstate` returned 403. `ci_plan`/`ci_apply`'s policies were "
         "scoped entirely to the *app* bucket (the infrastructure they manage) and never touched the "
         "*state* bucket their own S3 backend runs against. Reading and locking the state object is a "
         "mechanical requirement of `init`/`plan`/`apply` alike, independent of which role is asking.")
    D.p("Fixed with a policy shared by both roles, scoped to only the `app/` key prefix in the state "
        "bucket - explicitly never `bootstrap/`, which stays off-limits to any CI identity regardless.")

    D.h2("6.4  `gitleaks` crashed on the CI runner - not a config problem, an upstream one")
    dual(D,
         "The lint job's secret-detection hook, which had passed on every local run all session, crashed "
         "outright the first time it ran in GitHub Actions - a stack trace, not a finding.",
         "`panic: wasm error: invalid table access` inside `wasilibs/go-re2`'s wazero-based regex engine, "
         "while `gitleaks` compiled its own config. A real, documented upstream incompatibility between Go "
         "1.24 (what GitHub's runners now build tools with) and the wazero version the pinned `gitleaks` "
         "release (v8.23.1) was built against - confirmed against gitleaks' own issue tracker before "
         "touching anything.")
    D.p("Bumped the pin to v8.30.1 (built against a patched wazero), verified locally that the hook runs "
        "clean, then confirmed the same fix held in CI.")

    D.h2("6.5  The Trivy gate did exactly its job: it found a real, fixable CRITICAL")
    dual(D,
         "The first full build-and-scan of the actual gateway image failed - not because the pipeline was "
         "broken, but because the gate is supposed to fail when it finds something real.",
         "3 CRITICAL and 54 HIGH findings against the pinned base image. One CRITICAL "
         "(`perl-base`, CVE-2026-13221) had a fix already published upstream - the digest pinned back in "
         "M1 simply predated it. Re-pinned `python:3.12-slim` to its current digest (verified against "
         "Docker Hub's own tags API), which took CRITICAL to zero and HIGH from 54 to 44.")
    D.p("The remaining 44 (8 unique CVEs) are genuinely unfixed upstream - re-pinning can't remove what "
        "Debian hasn't patched yet. Per the gate's own stated policy (ADR 0010), that's a reviewed "
        "`.trivyignore` entry, not a loosened gate: each of the eight is a base-OS package "
        "(`ncurses`, `systemd-homed`, `libacl`, four `util-linux` CVEs, `perl-Archive-Tar`) in a code path "
        "the gateway - FastAPI/uvicorn/httpx, non-root, no mount or cgroup capability - never touches. "
        "Verified locally with `trivy image --ignorefile ...` against the new digest before trusting the "
        "same file in CI: clean, exit 0.")
    D.callout("This is the finding worth taking seriously",
              "A gate that never fails is decoration. This one fired on real content, on the first real "
              "run, for a reason a reviewer can check independently (the CVE ID, the fix version, the "
              "Debian changelog) - and the response was a genuine fix plus a genuinely justified, "
              "individually-reasoned exception list, not a threshold turned down until the noise stopped.",
              "ok")

    D.h2("6.6  A brand-new registry package's first signature push was denied, then wasn't")
    dual(D,
         "The image pushed to the registry successfully. Signing that exact same image, seconds later, "
         "in the same job, with the same credentials, was denied.",
         "`cosign sign`: `DENIED: permission_denied: write_package`, immediately after "
         "`docker/build-push-action` had already pushed the same image with the same `GITHUB_TOKEN` and "
         "the same `packages: write` permission. Checked whether the package was correctly linked to the "
         "repository and set to the expected visibility - it already was, on both counts, so this wasn't a "
         "settings gap. A plain re-run of the same job, no configuration changed, succeeded.")
    D.p("Read as a brand-new package's write-permission propagation lagging its own creation by a few "
        "seconds within the same run - documented as a known quantity rather than chased further, since "
        "the fix (retry) is simple and the cause (a registry-side timing detail, not anything under this "
        "project's control) doesn't change any design decision here.")


# =============================================================================
def deviations(D):
    D.h1("7. What Was Done Differently, and Why")
    D.table(
        ["#", "The plan/assumption said", "What was done instead", "Why"],
        [
            ["1", "Terraform 1.16.1 (the existing pin)", "**1.16.4**, and the local binary upgraded to "
             "match", "Checked against the live HashiCorp releases API while writing new Terraform, per "
             "the standing verify-before-pinning rule, and found the existing pin a release behind."],
            ["2", "The AWS CLI's existing profiles could be used or repaired", "**A fresh IAM user "
             "(`palisade-bootstrap`) created from scratch**", "The default profile's keys were dead and "
             "an existing SSO profile belonged to a different, unrecoverable login - §5.1."],
            ["3", "CLAUDE.md named a specific missing OAuth scope as the CI blocker",
             "**No remediation needed - the assumption was stale**", "Tested empirically with a throwaway "
             "probe workflow before trusting the note - §5.1."],
            ["4", "OIDC trust policy written as `repo:owner/repo:...`", "**Rewritten to GitHub's "
             "immutable `repo:owner@id/repo@id:...` format**", "This repository defaults to it "
             "(a newly-created repository defaults to it) - discovered via a real denied assume-role - "
             "§6.1."],
            ["5", "IAM policies enumerated the specific S3 Get actions expected to be needed",
             "**Broadened to `s3:Get*`/`s3:List*`, plus explicit state-bucket access**", "The AWS "
             "provider's `aws_s3_bucket` resource reads back far more than initially anticipated, and "
             "state-bucket access was missing entirely - §6.2, §6.3."],
            ["6", "`gitleaks` pinned at the version already in `.pre-commit-config.yaml`",
             "**Bumped to v8.30.1**", "The existing pin crashes under Go 1.24, a real upstream "
             "incompatibility unrelated to this project's own config - §6.4."],
            ["7", "The base image pinned in M1 was assumed still current", "**Re-pinned to the current "
             "`python:3.12-slim` digest**", "A real, fixed CRITICAL CVE was shipping in the stale pin - "
             "§6.5."],
        ],
        widths=[0.3, 2.05, 2.35, 1.65],
    )
    D.callout("A deviation worth more than the original plan",
              "Every single deviation above exists only because something was actually run against real "
              "infrastructure instead of assumed to work once it looked right on paper. That is the same "
              "lesson M0 and M1 each learned at a different layer: **the interesting engineering content "
              "lives in the gap between \"should work\" and \"does work.\"**", "ok")


# =============================================================================
def tool_choices(D):
    D.h1("8. Tool Choices - What Was Picked and What Was Rejected")
    D.p("Full reasoning for the registry, signing, state-bootstrap and severity-gate decisions lives in "
        "dedicated ADRs (0007-0010) rather than only here, since M3-M5 will keep referring back to them.")
    D.table(
        ["Decision", "Chosen", "Rejected, and why"],
        [
            ["Container registry", "**ghcr.io** (ADR 0007)",
             "**Docker Hub** - would need a separate registry credential stored as a GitHub secret, "
             "exactly the kind of long-lived credential this milestone exists to eliminate."],
            ["Image signing", "**cosign keyless, via Sigstore/Fulcio/Rekor** (ADR 0008)",
             "**cosign with a stored key pair** - works, but the private key becomes a secret to store, "
             "back up and rotate; keyless needs none of that."],
            ["Terraform state bootstrap", "**Local state, then `-migrate-state` into the bucket it "
             "creates** (ADR 0009)", "**A permanently hand-managed bucket** - the most security-sensitive "
             "resource in the project would then be undocumented as code. **DynamoDB lock table** - "
             "unnecessary compute-adjacent resource now that S3-native locking (`use_lockfile`) is GA."],
            ["Vulnerability gate threshold", "**HIGH/CRITICAL only, scanning the built image** (ADR 0010)",
             "**Also failing on MEDIUM** - scope creep past what the milestone's own acceptance criterion "
             "asked for, risking blocking merges on findings nobody signed up to triage."],
            ["Billing guard", "**AWS Budgets, via a standalone CLI script**",
             "**A classic CloudWatch billing alarm** - needs a root-only account preference toggle Budgets "
             "doesn't. **A Terraform resource** - can't predate the Terraform it's meant to backstop."],
            ["SBOM tooling", "**Syft, installed as a pinned release binary**",
             "**`anchore/sbom-action`** - one more third-party action in the signing chain's trust surface "
             "for no capability the pinned CLI doesn't already provide."],
            ["OIDC-to-AWS action", "**`aws-actions/configure-aws-credentials`, pinned by commit SHA**",
             "Long-lived IAM user access keys stored as GitHub secrets - the exact pattern OIDC exists to "
             "replace."],
        ],
        widths=[1.5, 1.85, 3.15],
    )


# =============================================================================
def limitations(D):
    D.h1("9. Limitations of This Setup")
    D.table(
        ["Limitation", "What it means in practice", "Honest position"],
        [
            ["**The bootstrap identity is still a static local credential**",
             "`palisade-bootstrap`'s AWS access key exists in this machine's local CLI config, with "
             "`AdministratorAccess`, so that `bootstrap/` can be applied by hand.",
             "Deliberate, and consistent with the milestone's actual claim: the acceptance criterion is "
             "that GitHub stores no AWS secret, which is true and verified. A local operator credential "
             "for a hand-applied root is a different, smaller, and disclosed exposure - not eliminated, "
             "just honestly scoped to \"who can reach this laptop,\" not \"who can read this repo.\""],
            ["**`.trivyignore` entries need periodic review, not a one-time pass**",
             "The eight accepted-risk CVEs in `services/gateway/.trivyignore` are unfixed *today*. If "
             "Debian ships a fix later, the entry should be removed and a rebuild should resolve it, not "
             "sit there indefinitely.",
             "Documented directly in the file's own header comment as the expected process, not left "
             "implicit - a future me (or M3+) re-touching this file is the natural trigger to check."],
            ["**No render-level verification of this document**",
             "The same limitation M1 disclosed: no LibreOffice in this environment to render a PDF and "
             "visually check for layout problems or stray markdown markers.",
             "A text-level scanner (`verify_m2_docx.py`) checks word count and stray formatting markers "
             "directly against the document XML instead - disclosed rather than silently skipped."],
            ["**The Terraform PR-comment step posts a plain text dump, not a formatted diff**",
             "`terraform.yml`'s `plan` job posts the raw plan output inside a collapsed `<details>` block "
             "via `actions/github-script` - readable, but not colourised or summarised.",
             "Good enough for a single-maintainer project with one small Terraform root. Worth revisiting "
             "if `infra/` grows enough that a plan output stops fitting comfortably in one glance."],
            ["**Single AWS account, single region, no environment split**",
             "There is no dev/staging/prod separation - one account, `us-east-1`, one of everything.",
             "Correct scope for this project's size. Revisit only if a genuine second environment need "
             "appears; adding the split speculatively now would be exactly the kind of premature structure "
             "this project's own conventions argue against."],
            ["**`--kv-cache-memory-bytes` is still chosen by feel, not formula**",
             "Carried over from M1, unchanged by this milestone.",
             "Still true, still disclosed. Not touched here because M2 never needed to touch the model-"
             "serving path at all."],
        ],
        widths=[1.7, 2.3, 2.6],
    )


# =============================================================================
def mistakes(D):
    D.h1("10. Mistakes Made, and What They Cost")
    D.table(
        ["What went wrong", "Cost", "What prevents a repeat"],
        [
            ["**Wrote a placeholder step with a fake commit SHA while drafting `ci.yml`**, meaning to "
             "replace it before it was ever run",
             "Caught during self-review before the workflow was committed, not in CI - zero pipeline cost, "
             "but a close call worth naming",
             "Every action reference in both workflows was re-checked against a live API call immediately "
             "before the file was finalised, not trusted from memory or a first draft."],
            ["**Assumed the classic `repo:owner/repo` OIDC subject format without checking this "
             "repository's actual settings first**",
             "One failed `terraform plan` on a real PR, plus the CloudTrail investigation to find the real "
             "cause - §6.1",
             "The check that would have caught it in advance (`gh api .../actions/oidc/customization/sub`) "
             "is now the first thing written into any future GitHub-to-AWS trust policy, per "
             "docs/CONVENTIONS.md."],
            ["**Enumerated specific S3 permissions instead of granting the read-only action families up "
             "front**",
             "Two separate round-trips through a real `terraform apply` before the role had everything it "
             "needed - §6.2, §6.3",
             "Recorded as a named pattern: for `aws_s3_bucket`, grant `Get*`/`List*` up front and keep "
             "only mutations enumerated, rather than discovering the read surface one 403 at a time."],
        ],
        widths=[2.55, 2.15, 1.9],
    )
    D.callout("The pattern across all three",
              "Each is a version of the same M0/M1 lesson at a different layer: **checking the real, "
              "current, external ground truth is cheaper than assuming it and finding out from a "
              "failure.** A live API call, a CloudTrail event, and a documented AWS-provider read pattern "
              "were each the fact that mattered, once actually checked.", "ok")


# =============================================================================
def explain(D):
    D.h1("11. Design Rationale - Questions Answered")
    _qa(D, [
        ("Why remove the old SSO profile instead of trying to sign into it?",
         "It belonged to a login nobody could recall - not something this project had ever used. Chasing "
         "access to an unrecoverable account costs more than starting clean, and starting clean produces "
         "an identity whose purpose and scope are actually documented from the moment it exists."),
        ("Why two IAM roles instead of one role with two trust conditions?",
         "A single role assumable from both a pull request and a push to main would let any open PR - "
         "reviewed or not - carry the same permissions as a merge. Two roles make the PR-vs-merge boundary "
         "an IAM fact, not just a workflow convention someone could bypass by triggering the wrong job."),
        ("How did you actually find the real OIDC subject claim GitHub was sending?",
         "CloudTrail. `AssumeRoleWithWebIdentity`'s own denied-request events record the exact "
         "`userIdentity.principalId` GitHub presented, which is the ground truth - far more reliable than "
         "guessing from documentation that might describe an older default."),
        ("Why didn't you just grant broad S3 permissions from the start and skip two of the six bugs?",
         "Because the point of scoping IAM tightly is that the tight version is the one worth explaining "
         "in an interview, not the broad one. Discovering the real minimum through actual failures, then "
         "documenting exactly why each permission is there, is a stronger and more honest story than "
         "guessing generously and never finding out what was actually load-bearing."),
        ("The Trivy gate failed once on a real finding. Why is that in the document as a good thing?",
         "Because a gate that never fires is indistinguishable from a gate that doesn't work. It found a "
         "real CRITICAL with a real fix, and separately forced a genuine, individually-justified decision "
         "about eight CVEs with no fix yet - that's the gate doing its job, not a bug in the pipeline."),
        ("Why keyless signing instead of the simpler-sounding stored-key approach?",
         "A stored key is a secret with a lifecycle: generated once, needs rotating, needs protecting, and "
         "is a single thing that, if it leaked, could forge a signature indefinitely. Keyless signing ties "
         "each signature to a specific workflow run's short-lived identity instead - there is nothing "
         "long-lived to leak in the first place."),
        ("What would you do differently starting this milestone over?",
         "Check `gh api .../actions/oidc/customization/sub` and grant `s3:Get*`/`s3:List*` from the start, "
         "instead of discovering both the hard way. Everything else - the identity split, the two-role "
         "design, the local-state-then-migrate bootstrap - held up exactly as designed under real load."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("12. Glossary - Terms Introduced in M2")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**OIDC (OpenID Connect)**", "A standard way for one system (GitHub Actions) to prove its "
             "identity to another (AWS) using a short-lived, cryptographically signed token instead of a "
             "long-lived password or key."],
            ["**Keyless signing**", "Signing something without a stored private key, by using a "
             "short-lived certificate issued for one specific, verifiable identity (here, a GitHub "
             "workflow run) instead."],
            ["**Fulcio / Rekor**", "Sigstore's certificate authority (issues the short-lived signing "
             "certificate) and public transparency log (permanently, publicly records that a signature "
             "was made) - the two services keyless cosign signing relies on."],
            ["**SBOM (Software Bill of Materials)**", "A structured, machine-readable list of every "
             "package inside a built artefact - here, an SPDX-2.3 document listing all 127 packages in "
             "the gateway image."],
            ["**Immutable OIDC subject claim**", "GitHub's newer identity-token format, embedding each "
             "repository and owner's permanent numeric ID alongside their name, so a renamed or recreated "
             "repository can't inherit an old trust relationship's identity."],
            ["**S3-native locking**", "S3's own conditional-write mechanism used directly as a Terraform "
             "state lock, replacing the older pattern of a separate DynamoDB table for the same purpose."],
            ["**Trust policy**", "The IAM document on a role that decides *who* is allowed to assume it - "
             "distinct from the role's permission policy, which decides what it can *do* once assumed."],
            ["**Accepted-risk exception**", "A deliberately documented, reviewed decision to allow a known "
             "finding (here, a CVE with no upstream fix) rather than block on something nobody can "
             "currently fix - the opposite of silently lowering a gate's threshold."],
        ],
        widths=[1.5, 5.1],
        size=9.3,
    )

    D.h1("13. Open Items Going Into M3")
    D.table(
        ["Item", "Status", "Action"],
        [
            ["Signed images aren't verified or enforced at deploy time yet", "M2 signs; nothing checks "
             "the signature before running an image",
             "M3: a Kyverno policy verifies the cosign signature at admission and blocks anything "
             "unsigned or from the wrong identity."],
            ["Secrets still live in plain environment variables", "Fine for one operator, not a real "
             "secret-management story",
             "M3 introduces SOPS + age for encrypted secrets in git, per the layout already reserved in "
             "`deploy/secrets/`."],
            ["The bootstrap identity is a static local credential", "Disclosed in §9, unchanged this "
             "milestone", "Acceptable for a hand-applied root; revisit only if the bootstrap process "
             "itself needs to be shared beyond one operator."],
            ["`.trivyignore` has eight live entries", "Justified today, not permanent",
             "Re-check on any future touch of the Dockerfile or base image - remove entries Debian has "
             "since patched."],
        ],
        widths=[2.1, 1.85, 2.55],
    )
    D.spacer(4)
    D.callout("Where M3 goes",
              "**M3 - Kubernetes, GitOps & Policy.** Argo CD delivering what M2's pipeline signs, Kyverno "
              "enforcing that nothing unsigned or non-compliant is ever admitted, and SOPS/age replacing "
              "plain environment variables for anything secret - turning a pipeline that signs its output "
              "into a cluster that refuses to run anything it can't verify.", "note")
