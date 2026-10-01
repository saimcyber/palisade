# -*- coding: utf-8 -*-
"""Content for the M3 engineering document."""
from docx_kit import *  # noqa: F403
from m0 import dual, _steps, _qa  # reuse the shared rendering helpers

SECTIONS = [
    "cover", "what_it_was_for", "starting_point", "decisions",
    "what_was_built", "how_it_was_done", "deep_dive", "deviations",
    "tool_choices", "limitations", "mistakes", "explain", "glossary_and_next",
]

# Filled in from the clean-rebuild run (make down && make up && make gitops).
REBUILD_RESULT = (
    "**Passed from a clean rebuild.** `make down && make up && make gpu-check && make gitops` "
    "(exit 0) brought a brand-new cluster to all four Applications Synced + Healthy, with every "
    "policy created before the first workload pod - no manual step beyond the age key file"
)


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
    r = p2.add_run("Engineering Log  ·  Milestone M3")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("Kubernetes, GitOps & Policy: the cluster enforces the rules itself")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M3 - Kubernetes, GitOps & Policy**"],
            ["Goal", "Git becomes the only route to production, and the cluster itself enforces the "
                     "rules rather than trusting the pipeline"],
            ["Result", "**Passed.** A `git push` deployed itself through Argo CD with no manual step, and "
                       "an unsigned image was refused at admission with a readable reason - recorded "
                       "with a signed positive control in `docs/evidence/m3/`"],
            ["Rebuild", REBUILD_RESULT],
            ["Delivery", "Argo CD app-of-apps (policies -> secrets -> workloads), auto-sync with prune "
                         "and self-heal, installed by Terraform's Helm provider"],
            ["Enforcement", "Kyverno: keyless signature verification, no `:latest`, non-root, drop ALL "
                            "capabilities, read-only root, memory limits. NetworkPolicy: default-deny, "
                            "no egress whatsoever from vLLM"],
            ["New code", "`deploy/charts/palisade`, `deploy/argocd`, `deploy/policies`, "
                         "`deploy/secrets`, `docker/model-verify`, `infra/terraform/cluster`, "
                         "`scripts/gitops-up.sh`, ADRs 0011-0020"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("Same structure as M0-M2, answering the same six standing questions.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**", "§4 What was built and **§5 How it was done**"],
            ["**2. What was done differently**, and why", "**§7 Deviations**"],
            ["**3. How it was done**", "§5, plus **§6** - the bugs that only a real sync exposed"],
            ["**4. What the limitations are**", "**§9 Limitations**"],
            ["**5. Why this tool/approach over the alternatives**", "**§8 Tool choices**, ADRs 0011-0020"],
            ["**6. Plain language and technical, both**", "Throughout, as **IN PLAIN LANGUAGE** / "
             "**TECHNICALLY** pairs"],
        ],
        widths=[2.1, 4.5],
    )
    D.callout("The one thing to take away from M3",
              "Every manifest in this milestone passed `helm lint`, a YAML check and a code review, and "
              "the first real sync still failed in five different ways. Three of them were silent: the API "
              "server accepted the object, dropped a field, and carried on. Only running the whole chain "
              "against a real cluster - and reading what the cluster actually held, not what git said - "
              "found them.", "ok")


# =============================================================================
def what_it_was_for(D):
    D.h1("1. What M3 Was For")
    D.h2("1.1  The goal, stated simply")
    dual(D,
         "M2 made the pipeline sign everything it builds. But a signature nobody checks is decoration. M3 "
         "moves the checking into the cluster itself: the cluster refuses to run anything that wasn't "
         "signed by this project's own build system, refuses anything that runs as root, and keeps the "
         "model server physically unable to talk to the internet. And it makes git the only way to change "
         "what runs - a change made by hand is quietly undone.",
         "Package the gateway and vLLM as one Helm chart; deliver it with Argo CD (app-of-apps, auto-sync, "
         "prune, self-heal); enforce keyless cosign verification plus a pod-security baseline with Kyverno "
         "at admission; isolate workloads with default-deny NetworkPolicies; verify model weights against "
         "a signed SHA-256 manifest before vLLM starts; and keep the one real secret SOPS/age-encrypted in "
         "git, decrypted inside Argo CD.")
    D.h2("1.2  The acceptance test")
    D.table(
        ["Criterion (from the plan)", "How it was demonstrated", "Evidence"],
        [
            ["A push to git deploys itself", "A chart fix was pushed; Argo CD polled, synced and rolled the "
             "gateway with `initiatedBy.automated: true` - no `kubectl`, no `argocd sync`",
             "`01-push-deploys-itself.txt`"],
            ["An unsigned image is refused, with a readable reason", "A tampered image (real gateway + one "
             "layer) pushed with a personal token was denied: `sigstore bundle verification failed: no "
             "matching signatures found`. The identical pod spec with the CI-signed digest was admitted",
             "`03-unsigned-image-refused.txt`"],
            ["(supporting) End to end through the Ingress", "Wrong key -> 401; demo key -> streamed tokens "
             "from the GPU", "`02-end-to-end-through-ingress.txt`"],
            ["(supporting) No egress from vLLM", "Raw-IP, DNS and hostname probes all blocked; controls "
             "show the network works where policy allows it", "`04-networkpolicy-enforcement.txt`"],
            ["(supporting) Self-heal", "A manual scale-up and a deleted default-deny policy were both "
             "reverted by Argo CD", "`05-argocd-self-heal.txt`"],
            ["(definition of done) Clean rebuild", "Fresh cluster to Synced + Healthy; policies created "
             "before any workload pod; a real request answered", "`06-clean-rebuild.txt`"],
        ],
        widths=[1.7, 3.3, 1.6],
        size=9.2,
    )
    D.callout("Why a positive control matters",
              "A refusal on its own proves little - a pod can be refused for a dozen reasons. The two pods "
              "in the refusal test are the gateway's own rendered spec, differing **only** in the image "
              "digest, so every baseline rule passes for both. The signature is the only variable left, and "
              "it alone decides the outcome.", "note")


# =============================================================================
def starting_point(D):
    D.h1("2. What Was True Going Into M3")
    D.table(
        ["Inherited from M2", "Consequence for M3"],
        [
            ["Images signed keylessly by `ci.yml` on `main`, pinned by digest",
             "Kyverno can check an exact identity (workflow path + ref + GitHub's OIDC issuer) - nothing "
             "to distribute, no key to rotate"],
            ["vLLM proven in-cluster on the RTX 3050 via CDI, with hard-won flags",
             "Those flags had to carry over unchanged into a chart, not be re-derived"],
            ["The gateway's API-key hashes lived in plain environment variables",
             "M3 had to move them into an encrypted, committed form"],
            ["No GitHub route into the laptop's cluster",
             "Delivery had to be **pull-based** (Argo CD polls git), not a CI job pushing to the cluster"],
        ],
        widths=[3.0, 3.6],
    )


# =============================================================================
def decisions(D):
    D.h1("3. Decisions, With the Decision Records")
    D.table(
        ["ADR", "Decision", "In one line, why"],
        [
            ["0011", "One Helm chart for gateway + vLLM", "They are one application; two charts would have "
             "to be kept in step by hand"],
            ["0012", "Model verification as a separate Job, not an init container", "NetworkPolicy can't give "
             "one container of a pod internet egress and another none"],
            ["0013", "Kyverno `ClusterPolicy`, four narrowly scoped policies", "Stable, well-documented API; "
             "signature check scoped to images this project actually signs"],
            ["0014", "Default-deny, egress claims per workload", "vLLM gets no egress block at all - the "
             "default-deny *is* its policy"],
            ["0015", "SOPS + age, decrypted by an Argo CD plugin", "Encrypted values in ordinary-looking "
             "YAML; the private key never enters git"],
            ["0016", "Argo CD + Kyverno via Terraform; app-of-apps after that", "One hand-applied root; "
             "everything else is git"],
            ["0017", "PVC health override", "`WaitForFirstConsumer` deadlocked sync-waves"],
            ["0018", "Kyverno `type: SigstoreBundle`", "The default Cosign verifier read a legacy "
             "signature layout with an empty certificate chain"],
            ["0019", "Numeric UID everywhere; vLLM hardened, not exempted", "The kubelet can't verify "
             "`runAsNonRoot` against a user *name*"],
            ["0020", "`make gitops`; policies sync before workloads", "A fresh cluster must never admit a "
             "pod before its policies exist"],
        ],
        widths=[0.5, 2.6, 3.5],
        size=9.2,
    )


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")
    D.h2("4.1  The shape of the deployment")
    D.code(
        "git (main) --poll--> Argo CD  root app-of-apps\n"
        "                       |-- wave -1  palisade-policies  Kyverno ClusterPolicies + NetworkPolicies\n"
        "                       |-- wave  0  palisade-secrets   SOPS-encrypted Secret -> CMP sidecar -> Secret\n"
        "                       '-- wave  1  palisade (Helm)\n"
        "                                     wave -1  PVC vllm-hf-cache\n"
        "                                     wave  0  Job model-verify   (Sync hook: signed manifest + SHA-256)\n"
        "                                     wave  1  Deployment vllm     (GPU via CDI, zero egress)\n"
        "                                     wave  2  Deployment gateway  (Ingress -> gateway -> vllm:8000)\n"
        "every Pod --> Kyverno admission webhook --> verifyImages + baseline --> admitted / denied")
    D.h2("4.2  The pieces")
    D.table(
        ["Component", "What it does", "Where"],
        [
            ["Helm chart", "Gateway (Deployment, Service, Ingress, ConfigMap, PDB), vLLM (Deployment, "
             "Service, PVC), model-verify Job, namespace", "`deploy/charts/palisade/`"],
            ["Probes", "vLLM: startup probe budget of 60 x 10 s so a model load is never mistaken for a hang; "
             "gateway readiness only true once vLLM answers", "chart templates"],
            ["Argo CD", "Root app + three child apps; auto-sync, prune, self-heal", "`deploy/argocd/`"],
            ["Kyverno policies", "Signature verification; disallow `:latest`; non-root, drop ALL, "
             "read-only root, memory limits", "`deploy/policies/kyverno-*.yaml`"],
            ["NetworkPolicies", "Default-deny; gateway -> vLLM/DNS/Redis; vLLM ingress from gateway only; "
             "model-verify -> DNS + 443", "`deploy/policies/networkpolicy-*.yaml`"],
            ["model-verify", "Verifies the manifest's keyless signature, downloads the pinned revision, "
             "checks every file's SHA-256, refuses on any mismatch", "`docker/model-verify/`"],
            ["SOPS secret", "API-key hashes, encrypted to an age key", "`deploy/secrets/`"],
            ["Bootstrap", "age key -> Terraform -> wait -> pre-pull -> root app -> wait", "`make gitops`"],
        ],
        widths=[1.3, 3.6, 1.7],
        size=9.2,
    )
    D.h2("4.3  The security posture, pod by pod")
    D.table(
        ["Pod", "UID", "Root FS", "Caps", "Egress", "Image trust"],
        [
            ["gateway", "999", "read-only", "none", "DNS, vLLM, Redis", "signed by `ci.yml`"],
            ["vLLM", "999", "read-only", "none", "**none**", "upstream tag (see §9)"],
            ["model-verify", "999", "read-only", "none", "DNS, 443", "signed by `model-verify-image.yml`"],
        ],
        widths=[1.1, 0.6, 0.9, 0.6, 1.6, 1.8],
        size=9.2,
    )

    D.h2("4.4  How a change reaches the cluster")
    dual(D,
         "Nobody deploys anything. A change is a commit. A program inside the cluster keeps reading the "
         "repository, notices the commit, and makes the cluster match it. If someone changes the cluster "
         "by hand instead, the same program notices the difference and puts it back.",
         "Argo CD polls `main`, renders the chart and the policy/secret directories, diffs them against "
         "live state and applies the difference in sync-wave order. `automated.prune` deletes what git "
         "no longer declares; `selfHeal` re-applies on any live drift. New images arrive the same way: "
         "CI's bump-digest job opens a PR changing one digest line, and merging it is the deployment.")

    D.h2("4.5  What the network can and cannot do")
    D.table(
        ["Probe (raw TCP connect from inside the pod)", "Result", "What it proves"],
        [
            ["vLLM -> 1.1.1.1:443 (raw IP)", "**blocked**", "No egress, and not merely a DNS failure"],
            ["vLLM -> kube-dns :53", "**blocked**", "Even name resolution is denied"],
            ["vLLM -> huggingface.co:443", "**blocked**", "The model cannot fetch or phone home"],
            ["gateway -> vllm:8000", "connected", "Control: the allowed path works"],
            ["gateway -> 1.1.1.1:443", "blocked", "The gateway has no internet either"],
            ["other namespace -> vllm:8000", "blocked", "Only the gateway may reach the model"],
            ["unpoliced pod -> 1.1.1.1:443", "connected", "Control: the cluster has internet at all"],
        ],
        widths=[2.6, 0.9, 3.1],
        size=9.2,
    )
    D.p("k3s enforces NetworkPolicy with its embedded kube-router controller, which rejects rather than "
        "drops - hence `Connection refused` instead of a timeout in the raw transcript.")


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done")
    _steps(D, [
        ("Chart first, carrying M1's settings unchanged",
         "`runtimeClassName: nvidia`, the CDI annotation, `enableServiceLinks: false`, "
         "`--kv-cache-memory-bytes=512M` and `VLLM_WSL2_ENABLE_PIN_MEMORY=1` were templated verbatim. "
         "Every image is pinned by digest; CI's bump-digest jobs open a PR that rewrites the digest, so a "
         "new build reaches the cluster only through a reviewed commit."),
        ("Argo CD and Kyverno through Terraform",
         "`infra/terraform/cluster` installs both with the Helm provider. Kyverno runs with its TUF trust "
         "root enabled; Argo CD gets a SOPS plugin sidecar and two health overrides (PVC, Application)."),
        ("Policies written to admit the chart, not patched after",
         "Every `securityContext` field in the chart is also a Kyverno rule, so a regression in the chart "
         "is a denied pod, not a silently weaker one."),
        ("Signature verification made to actually pass",
         "The longest single investigation of the milestone (ADR 0018): Kyverno refused images that "
         "`cosign verify` accepted. Decoding the stored certificate showed an empty intermediate chain "
         "written by cosign's legacy path; switching the policy to `type: SigstoreBundle` and signing with "
         "plain cosign defaults fixed it. Proven on throwaway policies before production config changed."),
        ("First real sync - five more failures, one at a time",
         "Each is in §6. The pattern for all of them: reproduce on a scratch copy rendered with "
         "`helm template` inside the real namespace (so Kyverno stays in the loop), fix in the chart, "
         "push, and let Argo CD apply it."),
        ("Acceptance demonstrations, each with a control",
         "Push-deploys-itself, unsigned refusal, end-to-end, NetworkPolicy and self-heal - recorded as "
         "plain-text transcripts in `docs/evidence/m3/`."),
        ("Bootstrap made reproducible",
         "`make gitops` turned shell history into an ordered, idempotent script; child Applications got "
         "sync-waves so policies exist before any workload is admitted (ADR 0020)."),
    ])
    D.h2("5.1  The commands that matter")
    D.code(
        "make up && make gpu-check            # M0: cluster + GPU\n"
        "make gitops                          # age key, Argo CD + Kyverno, root app, wait for Synced\n"
        "kubectl -n argocd get applications   # all four Synced / Healthy\n"
        "git push origin main                 # the only way to change what runs\n"
        "kubectl apply -f unsigned-pod.yaml   # -> denied by verify-palisade-image-signatures")


# =============================================================================
def deep_dive(D):
    D.h1("6. Deep Dive - What Only a Real Sync Found")
    D.p("Once Kyverno admitted the signed images, the first end-to-end sync exposed five defects. None "
        "was visible to `helm lint`, YAML validation or review. Three were **silent**: the cluster accepted "
        "the object and simply did something other than what git said.")
    rows = [
        ("6.1  Named users vs runAsNonRoot",
         "The pods were let in, then never started. The security rule said 'not root', but the images only "
         "named their user (`palisade`), and Kubernetes won't take a name on trust.",
         "`CreateContainerConfigError: image has non-numeric user (palisade), cannot verify user is "
         "non-root`. Kyverno checks the spec; the kubelet checks the image, and needs a number. Fix: "
         "`runAsUser`/`runAsGroup: 999` from one chart value - no rebuild, no re-signing (ADR 0019)."),
        ("6.2  vLLM had no security context at all",
         "The model server ran as the all-powerful root user. The policy would have blocked it the moment "
         "the sync reached it - so the fix was to make it run safely, not to make an exception.",
         "No `runAsNonRoot`, default capabilities, writable root. Hardened to UID 999, `drop: [ALL]`, "
         "`readOnlyRootFilesystem`, with emptyDirs for `HOME`, `XDG_CACHE_HOME`, `VLLM_CACHE_ROOT`, "
         "`TRITON_CACHE_DIR`; `HF_HUB_OFFLINE=1` and a pinned `--revision`; `HF_HUB_CACHE` aligned with "
         "the verifier's layout. The pre-agreed fallback, a scoped `PolicyException`, was not needed."),
        ("6.3  A hook that could never fail",
         "The deployment waited forever on a job that could neither succeed nor fail.",
         "A pod stuck in `CreateContainerConfigError` is not a Job *failure*, so `backoffLimit` never "
         "fired and the Argo CD Sync hook blocked the operation indefinitely. Fix: "
         "`activeDeadlineSeconds: 900` - a hang becomes a visible failed sync."),
        ("6.4  A sync-wave deadlock",
         "The front door waited for the model to be ready, and the model was only started once the front "
         "door was ready.",
         "Gateway in default wave 0, its `/readyz` true only once vLLM answers; vLLM in wave 1, which Argo "
         "CD starts only when wave 0 is Healthy. Fix: gateway to wave 2."),
        ("6.5  A field the API server silently dropped",
         "The gateway ran without any of its settings - including the list of valid API keys - and nothing "
         "complained.",
         "`prefix: PALISADE_` was nested inside `configMapRef`/`secretRef` instead of on the `envFrom` "
         "entry. The API server discards unknown fields, so the gateway saw no `PALISADE_*` variables, and "
         "Argo CD saw a permanent diff it re-applied on every reconcile. Found by reading `kubectl diff`, "
         "not by any failure. The same class of bug made the root app OutOfSync forever: an all-default "
         "`directory: {recurse: false}` block that Argo CD normalises away."),
    ]
    for title, plain, tech in rows:
        D.h2(title)
        dual(D, plain, tech)
    D.h2("6.6  Before all of this: the signature that verified everywhere except in the cluster")
    dual(D,
         "The cluster refused images this project had genuinely signed. The standard checking tool, run by "
         "hand, said the signatures were fine. Four plausible fixes were tried and disproved before the real "
         "cause was found by opening the stored signature and reading the certificate inside it.",
         "Kyverno reported `no signatures found` for images `cosign verify` accepted. The policy's "
         "`verifyImages` set no `type:`, which defaults to `Cosign` - Kyverno's legacy verifier for the "
         "pre-bundle signature layout - while cosign v3 writes the modern Sigstore bundle. GHCR has no OCI "
         "1.1 Referrers API, so the bundle lands under a tag the legacy verifier never looks for.")
    D.table(
        ["Attempt", "Why it looked right", "How it was disproved"],
        [
            ["1. `--registry-referrers-mode=legacy`", "Named exactly the layout mismatch",
             "Its own help text: it governs what cosign *fetches*, not what `sign` writes. A redeploy "
             "failed identically"],
            ["2. Pin Kyverno below a known `verifyImages` regression", "An upstream issue described the "
             "same symptom", "Downgraded and tested live: identical failure on identical images"],
            ["3. `--new-bundle-format=false --use-signing-config=false`", "These really do change the "
             "write path", "Kyverno now found the signature, then failed: `x509: certificate signed by "
             "unknown authority`. Decoding it showed an **empty intermediate chain**"],
            ["4. Enable Kyverno's TUF trust root", "A frozen root could explain an unknown authority",
             "A real improvement (kept), but the same error persisted"],
            ["**Fix:** `type: SigstoreBundle`, plain cosign defaults", "Reads cosign's unmodified output",
             "Proven on throwaway policies against the live cluster, then on the production digests"],
        ],
        widths=[2.0, 1.9, 2.7],
        size=9.0,
    )
    D.p("The standalone `cosign verify` never noticed the empty chain because it completes the chain "
        "from its own cache. Kyverno's verifier does not, which is why one tool passed and the other "
        "failed on the same bytes. The lesson recorded in ADR 0018 is procedural: the decisive step was "
        "reading the artefact the failing component reads, and it came fourth when it should have come "
        "first.")

    D.h2("6.7  The refusal, verbatim")
    D.p("This is what an operator sees when the tampered image is applied - the output M3's acceptance "
        "criterion asks for, unedited apart from line wrapping:")
    D.code(
        "$ kubectl apply -f unsigned-pod.yaml\n"
        "Error from server: admission webhook \"mutate.kyverno.svc-fail\" denied the request:\n"
        "resource Pod/palisade/gateway-unsigned was blocked due to the following policies\n"
        "verify-palisade-image-signatures:\n"
        "  verify-gateway-signature: 'failed to verify image\n"
        "    ghcr.io/saimcyber/palisade-gateway@sha256:c07cca10...:\n"
        "    .attestors[0].entries[0].keyless: sigstore bundle verification failed:\n"
        "    no matching signatures found'\n"
        "\n"
        "$ kubectl apply --dry-run=server -f signed-pod.yaml      # identical spec, CI-signed digest\n"
        "pod/gateway-signed created (server dry run)")
    D.p("The same refusal fires for a Deployment (Kyverno auto-generates the rule for pod controllers), so "
        "it would stop a bad digest arriving through Argo CD just as it stops a direct `kubectl apply`. "
        "The tampered image was deleted from the registry after the test; the transcript keeps its digest.")

    D.callout("Lesson",
              "**Synced is not the same as correct.** Two of these bugs left Argo CD reporting a perfectly "
              "plausible state. The check that found them was comparing what the cluster actually held "
              "(`kubectl diff`, `env` inside the pod) with what git declared.", "warn")


# =============================================================================
def deviations(D):
    D.h1("7. Deviations From the Plan")
    D.table(
        ["Plan said", "What was done", "Why"],
        [
            ["Model verification as an **init container**", "A separate Job, run as an Argo CD Sync hook "
             "before vLLM", "NetworkPolicy is per pod: an init container sharing vLLM's pod would force "
             "either internet egress for vLLM or none for the verifier (ADR 0012)"],
            ["Qwen2.5-0.5B", "Qwen3-0.6B", "Carried over from M1, where it was the model proven to fit"],
            ["Gateway to vLLM **and Redis** only", "Redis rule written, but Redis does not exist yet",
             "Redis arrives in M4; the rule is inert until then and needs no edit when it lands"],
            ["(not in plan) run upstream vLLM as shipped", "Hardened to the same baseline as first-party pods",
             "An exemption for the most-privileged workload would have hollowed out the policy (ADR 0019)"],
            ["(not in plan) bootstrap order", "Policies forced to sync before workloads",
             "Otherwise a fresh cluster could admit pods before policies exist (ADR 0020)"],
            ["Signing as M2 left it", "Kyverno policy changed to `type: SigstoreBundle`",
             "The default verifier could not validate the stored signature format (ADR 0018)"],
        ],
        widths=[1.7, 2.2, 2.7],
        size=9.2,
    )


# =============================================================================
def tool_choices(D):
    D.h1("8. Tool Choices - and What Was Rejected")
    D.table(
        ["Chose", "Over", "Because"],
        [
            ["**Argo CD**", "Flux", "Application-level health and sync status visible in one object; "
             "app-of-apps maps directly onto policies / secrets / workloads"],
            ["**Kyverno**", "OPA Gatekeeper", "Policies are YAML, not Rego, and `verifyImages` does keyless "
             "cosign verification natively"],
            ["Kyverno `ClusterPolicy`", "Newer CEL `ImageValidatingPolicy`", "Stable, documented surface at "
             "the pinned version (ADR 0013)"],
            ["**SOPS + age**", "Sealed Secrets, External Secrets", "No cluster-side controller holding a "
             "key per cluster, no cloud secret store needed; diffable, reviewable encrypted YAML"],
            ["age", "GPG", "No keyring, no web of trust, two short strings"],
            ["Terraform Helm provider", "`helm install` by hand", "The add-ons are versioned, planned and "
             "reproducible like every other piece of infrastructure"],
            ["Chart-level numeric UID", "Rebuilding images with `USER 999`", "Fixes it where the kubelet "
             "reads it, without re-signing three images (both would be best - §9)"],
        ],
        widths=[1.6, 1.6, 3.4],
        size=9.2,
    )


# =============================================================================
def limitations(D):
    D.h1("9. Limitations")
    D.p("What this setup genuinely cannot do, stated plainly.")
    D.table(
        ["Limitation", "Why it exists / what would fix it"],
        [
            ["vLLM's upstream image is trusted by **tag**, not digest or signature",
             "It is not this project's to sign. Pinning `vllm/vllm-openai` by digest is the next step; "
             "verifying the vLLM project's own provenance would be the one after"],
            ["Model verification needs Sigstore and Hugging Face reachable at deploy time",
             "It fails closed - one attempt hit a network `EOF`, refused, and the retry passed. A mirrored "
             "TUF root would remove the dependency"],
            ["Argo CD **polls** git; there is no webhook",
             "GitHub cannot reach a laptop's cluster. Deploys lag a push by the poll interval"],
            ["Secret rotation needs a rollout restart",
             "Env vars from a Secret are read once at start. No Reloader is installed"],
            ["The resource-limits rule checks **memory only**, though its message says CPU and memory",
             "Deliberate for vLLM's bursty CPU, but the message should say so"],
            ["Baseline rules inspect `containers`, not `initContainers`",
             "No init containers exist today; a future one would not be checked"],
            ["Signature verification is scoped to the `palisade` namespace",
             "A pod in another namespace could run an unsigned `ghcr.io/saimcyber/*` image"],
            ["UID 999 is coupled to what `useradd --system` assigned",
             "Pinning `USER 999:999` in the Dockerfiles would remove the coupling"],
            ["The age private key is a single local file",
             "Lose it and every secret must be re-encrypted to a new key (ADR 0015)"],
            ["Ingress is plain HTTP on localhost", "TLS termination is out of scope for a local cluster"],
            ["One node, one GPU", "No HA: vLLM uses `Recreate`; the PDB protects the gateway only"],
            ["Kyverno now warns that `kyverno.io/v1 ClusterPolicy` is deprecated",
             "Chosen deliberately for stability (ADR 0013); migrating to `ValidatingPolicy` / "
             "`ImageValidatingPolicy` is required before it is removed"],
            ["A flaky network can fail a sync several times before it converges",
             "Seen on the clean rebuild: the verify Job's deadline plus Argo CD's automated retry "
             "recovered it unaided, but convergence time depends on the link"],
        ],
        widths=[2.7, 3.9],
        size=9.2,
    )


# =============================================================================
def mistakes(D):
    D.h1("10. Mistakes and What They Taught")
    D.table(
        ["Mistake", "Lesson"],
        [
            ["Four wrong fixes for the signature failure before decoding the actual certificate",
             "Read the artefact the verifier reads. The answer was in the stored certificate the whole time"],
            ["Writing `securityContext` for the first-party pods but none for vLLM",
             "The workload most often waved through is the one most worth hardening"],
            ["Assuming Synced meant correct",
             "Compare live state with git - `kubectl diff` found two bugs nothing else reported"],
            ["Debugging non-root GPU failures when the GPU itself was offline",
             "Run the lowest-level check first: `nvidia-smi` on the host before blaming a pod's settings. "
             "The laptop had dropped into an integrated-graphics-only mode"],
            ["Keeping no copy of the raw demo API key",
             "Correct for a real secret, awkward for a demo. A second demo key now lives outside git"],
        ],
        widths=[2.8, 3.8],
    )


# =============================================================================
def explain(D):
    D.h1("11. Design Rationale - Questions Answered")
    _qa(D, [
        ("Why enforce signatures in the cluster when CI already signs everything?",
         "Because CI is not the only thing that can write to the registry. A leaked token can push an "
         "image; it cannot produce a signature from this repository's workflow identity. The refusal test "
         "models exactly that."),
        ("Why not exempt vLLM from the pod-security baseline? It's third-party.",
         "That is the argument for hardening it. It is the largest, most privileged and least reviewed "
         "process in the system. Running it non-root and read-only cost a handful of environment variables."),
        ("Why a Job instead of an init container for model verification?",
         "NetworkPolicy works per pod. The verifier needs the internet; vLLM must never have it. Two pods "
         "is the only way both can be true at once."),
        ("What stops someone with kubectl from changing the cluster by hand?",
         "Nothing at the API - they have the rights. Argo CD's self-heal reverts it on the next reconcile, "
         "including a deleted default-deny NetworkPolicy, as recorded in the evidence."),
        ("Why are policies forced to sync first?",
         "Kyverno only judges pods at admission. A pod admitted before the policy existed is never "
         "re-judged until it restarts. Ordering removes that window instead of detecting it later."),
        ("What would you change starting over?",
         "Render the chart and `kubectl diff` it against a live cluster from day one, and pin numeric "
         "UIDs in every Dockerfile from the first build."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("12. Glossary - Terms Introduced in M3")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**GitOps**", "Running a system so that a git repository is the only description of what "
             "should run, and an agent makes the cluster match it"],
            ["**App-of-apps**", "One Argo CD Application whose only job is to create other Applications"],
            ["**Sync-wave**", "An ordering number; Argo CD applies lower waves first and waits for them to "
             "be healthy"],
            ["**Self-heal**", "Argo CD undoing any change made to the cluster that git does not contain"],
            ["**Admission controller**", "A gatekeeper the Kubernetes API consults before storing an object; "
             "it can reject it with a reason"],
            ["**Kyverno**", "A policy engine that runs as an admission controller, with policies written as YAML"],
            ["**NetworkPolicy**", "A firewall rule for pods, selected by labels"],
            ["**SOPS / age**", "A tool that encrypts only the values in a YAML file, and the small modern "
             "encryption tool it uses"],
            ["**CMP (Config Management Plugin)**", "A sidecar that transforms files before Argo CD reads "
             "them - here, decrypting secrets"],
            ["**Sync hook**", "A resource Argo CD runs as a step of the sync itself, such as the verify Job"],
            ["**Startup probe**", "A health check that gives a slow-starting container time before the "
             "liveness check can kill it"],
        ],
        widths=[1.7, 4.9],
        size=9.3,
    )
    D.h1("13. Open Items Going Into M4")
    D.table(
        ["Item", "Action"],
        [
            ["Redis NetworkPolicy rule is inert", "M4 adds Redis for API keys and rate limits; the rule applies "
             "unchanged"],
            ["vLLM image trusted by tag", "Pin by digest"],
            ["Admission denials are only events", "M4's Security dashboard counts them as a metric"],
            ["Secret rotation needs a restart", "Consider a reloader once key issuance moves to Redis"],
        ],
        widths=[2.6, 4.0],
    )
    D.spacer(4)
    D.callout("Where M4 goes",
              "**M4 - Platform features and observability.** Multi-tenant API keys, token budgets, a prompt "
              "guard and four dashboards - built on a cluster that now refuses anything it cannot verify.",
              "note")
