# -*- coding: utf-8 -*-
"""Content for the M5 engineering document."""
from docx_kit import *  # noqa: F403
from m0 import dual, _steps, _qa  # reuse the shared rendering helpers

SECTIONS = [
    "cover", "what_it_was_for", "starting_point", "decisions",
    "what_was_built", "how_it_was_done", "deep_dive", "deviations",
    "tool_choices", "limitations", "mistakes", "explain", "glossary_and_next",
]

REBUILD_RESULT = (
    "**Passed from a clean rebuild.** `make down && make up && make gpu-check && make gitops` brought a "
    "brand-new cluster to all six Applications Synced + Healthy, with the gateway running at the digest "
    "that carries both chaos-day fixes and every alert rule present including the one chaos day itself "
    "found missing - `docs/evidence/m5/08-clean-rebuild.txt`. A separate `git clone` from GitHub into a "
    "directory with no relationship to the working copy then ran the gateway's full test suite (56 "
    "passed) and the environment doctor script (29 passed) with zero setup beyond what the repository "
    "itself declares - `docs/evidence/m5/09-fresh-clone.txt`. Two deliverables from the plan's own list "
    "remain open: the Cloudflare Tunnel demo and the short demo video, the second deliberately deferred."
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
    r = p2.add_run("Engineering Log  ·  Milestone M5")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("Resilience and Proof: breaking it on purpose, and writing down what actually happened")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M5 - Resilience, Proof and Storytelling**"],
            ["Goal", "Prove the platform performs under load, survives real failures, and can be "
                     "understood by a stranger without the person who built it in the room"],
            ["Result", "**Load test, chaos day, and all five engineering documents complete.** Chaos day "
                       "found two real bugs (fixed, tested, verified live) and one genuine observability "
                       "gap (also fixed). A clean rebuild and a fresh GitHub clone both passed. The "
                       "Cloudflare Tunnel demo is the one deliverable still open"],
            ["Rebuild", REBUILD_RESULT],
            ["Gateway", "Deliberate load shedding in front of vLLM (`InFlightLimiter`, ADR 0024); both "
                       "chaos-day bugs fixed in `upstream.py` and `routes/chat.py`"],
            ["Chaos day", "Six hypotheses written before any experiment ran; five run for real against "
                          "the live cluster - kill vLLM mid-stream, stall Redis, lose Redis, a validly "
                          "signed image from the wrong workflow, an old but genuinely signed image, and "
                          "VRAM exhaustion"],
            ["New docs", "`docs/THREAT-MODEL.md`, `docs/SLO.md`, `docs/RUNBOOK.md`, `docs/COST.md`, "
                        "`docs/ARCHITECTURE.md`, `docs/POSTMORTEM-001.md`, ADRs 0024-0025"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("Same structure as M0-M4, answering the same six standing questions.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**", "§4 What was built and **§5 How it was done**"],
            ["**2. What was done differently**, and why", "**§7 Deviations** - a wrong hypothesis and a "
             "wrong first conclusion, both corrected in the open"],
            ["**3. How it was done**", "§5, plus **§6** - a VRAM test that measured the wrong thing twice"],
            ["**4. What the limitations are**", "**§9 Limitations**"],
            ["**5. Why this tool/approach over the alternatives**", "**§8 Tool choices**, ADRs 0024-0025"],
            ["**6. Plain language and technical, both**", "Throughout, as **IN PLAIN LANGUAGE** / "
             "**TECHNICALLY** pairs"],
        ],
        widths=[2.1, 4.5],
    )
    D.callout("The one thing to take away from M5",
              "The two most damaging bugs in this entire project were never caught by a test, an alert, "
              "or a code review - because nothing had ever actually broken the dependencies they depend "
              "on. Both were found by a single `kubectl delete pod` and a single `redis-cli CLIENT "
              "PAUSE`. An audit-logging platform's correctness claims are only as strong as the failure "
              "modes someone has actually gone looking for.", "ok")


# =============================================================================
def what_it_was_for(D):
    D.h1("1. What M5 Was For")
    D.h2("1.1  The goal, stated simply")
    dual(D,
         "M0-M4 built a working system. M5 is the part that actually gets it read by a hiring manager: "
         "proof it holds up under load, proof it survives real failures with a plan for what happens "
         "next, and documents that let a stranger understand what it does and does not do without asking "
         "the person who built it.",
         "Run a k6 saturation test to find the real breaking point, add deliberate load shedding so that "
         "breaking point fails gracefully instead of falling over, spend a chaos day deliberately "
         "breaking the live cluster and recording exactly what happens, and write the five documents a "
         "real production system is expected to have but almost no portfolio project does: a threat "
         "model, an SLO backed by measured numbers, a runbook, a cost analysis, and a blameless "
         "postmortem of a real failure.")
    D.h2("1.2  The acceptance test")
    D.table(
        ["Criterion (from the plan)", "How it was demonstrated", "Evidence"],
        [
            ["A stranger can understand the project without the builder in the room", "Five standalone "
             "documents, each answering one real operational question, cross-linked from the README "
             "above the fold", "`docs/*.md`"],
            ["`git clone && make up` reproduces the platform on a clean machine", "A real `git clone` from "
             "GitHub into a directory with no relationship to the working copy; full test suite and "
             "environment doctor both passed with zero extra setup", "`09-fresh-clone.txt`"],
            ["(supporting) The acceptance command passes from a clean rebuild, not an already-warm cluster",
             "`make down && make up && make gitops`: all six Applications Synced + Healthy, the correct "
             "gateway digest, all seven alert rules, a real end-to-end completion", "`08-clean-rebuild.txt`"],
            ["(supporting) Chaos day: break it deliberately, write down what actually happened",
             "Six hypotheses written first; five run for real; two real bugs found, fixed and verified "
             "live; one hypothesis proven wrong in an informative way", "`docs/evidence/m5/`"],
        ],
        widths=[2.3, 3.2, 1.5],
        size=8.8,
    )
    D.callout("Why the hypotheses were written before the experiments",
              "A hypothesis adjusted after seeing the result isn't a hypothesis, it's a rationalisation. "
              "`docs/evidence/m5/chaos-hypotheses.md` was committed before the first `kubectl delete pod` "
              "ran, specifically so that being wrong - which happened, more than once - would show up on "
              "the page rather than get quietly smoothed into 'yes, as expected.'", "note")


# =============================================================================
def starting_point(D):
    D.h1("2. What Was True Going Into M5")
    D.table(
        ["Inherited from M4", "Consequence for M5"],
        [
            ["M4's open items: no Alertmanager receiver, `estimate_tokens` can under-reserve",
             "Neither was in scope for M5's own acceptance test; both are still open, now carried forward "
             "a second milestone rather than silently dropped"],
            ["vLLM's `--kv-cache-memory-bytes=512M` fix already in place from M1's GPU-in-k3d "
             "investigation", "The chaos day's VRAM experiment inherited this exact configuration - it "
             "turned out to matter more than expected, §6"],
            ["No load-shedding mechanism anywhere in the request path", "A fixed `max_in_flight_upstream_"
             "requests` ceiling had to be designed, built and tested from zero before the saturation test "
             "could show anything other than an unbounded queue"],
            ["Every exception handler in `upstream.py`/`chat.py` covered only the failure modes that had "
             "already been observed (`ConnectError`, `TimeoutException`, `HTTPStatusError`)",
             "Neither `httpx.RemoteProtocolError` nor any `redis.exceptions.RedisError` subtype had ever "
             "been triggered before - chaos day was the first time anything actually forced either "
             "dependency to fail mid-request, §4 and §6"],
        ],
        widths=[3.0, 3.6],
    )


# =============================================================================
def decisions(D):
    D.h1("3. Decisions, With the Decision Records")
    D.table(
        ["ADR", "Decision", "In one line, why"],
        [
            ["0024", "Load shedding via a plain in-process integer counter "
             "(`InFlightLimiter`), not `asyncio.Semaphore` or a Redis-backed limit",
             "Single-threaded cooperative asyncio has no race between check-then-increment with no "
             "`await` in between - a plain counter is correct and needs nothing else to fail"],
            ["0025", "k6 saturation test runs twice: in CI against a dependency-free Python stub "
             "upstream, and separately by hand against the real GPU for real numbers",
             "A self-hosted GitHub Actions runner on this public repo would let any fork's PR execute "
             "code on the machine holding this project's signing material - rejected outright"],
        ],
        widths=[0.5, 2.6, 3.5],
        size=9.2,
    )


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")
    D.h2("4.1  Load shedding, in front of vLLM")
    D.code(
        "every request, immediately before the call to vLLM:\n"
        "  limiter.try_acquire()  - plain int, no await between check and increment\n"
        "    True  -> proceed; limiter.release() in finally\n"
        "    False -> 503, palisade_load_shed_total += 1, the budget reservation is refunded\n"
        "                                                   (the upstream was never called)")
    D.h2("4.2  The two bugs chaos day actually found")
    D.table(
        ["Bug", "What was wrong", "Fix"],
        [
            ["`httpx.RemoteProtocolError` uncaught in the streaming path", "vLLM's connection closing "
             "mid-stream propagated past `relay()`'s own `except UpstreamError` clause (wrong exception "
             "type) - `status_code` never left its default `\"200\"`, so the audit log reported a "
             "truncated, failed stream as a success", "Caught explicitly in `upstream.py`, raised as "
             "`UpstreamError(502, ...)` - audit log now correctly reports `outcome=upstream_error, "
             "status=502`"],
            ["`redis.exceptions.RedisError` uncaught anywhere in the request handler", "A paused Redis "
             "outlasting the client's own ~5s socket timeout raised from the very first Redis call - "
             "Starlette's generic handler returned a bare `500` with **no audit line at all**, worse than "
             "the first bug since there was no record whatsoever", "`create_chat_completion` is now a "
             "thin wrapper catching `RedisError` and returning a clean, audited `503` "
             "(`outcome=redis_unavailable`)"],
        ],
        widths=[1.6, 2.8, 2.1],
        size=8.8,
    )
    D.h2("4.3  The five documents")
    D.table(
        ["Document", "What it answers"],
        [
            ["`THREAT-MODEL.md`", "STRIDE mapped to real controls and real evidence files, plus an "
             "explicit \"not modeled\" section (prompt injection as defence-in-depth only, training-data "
             "poisoning and GPU side-channels out of scope)"],
            ["`SLO.md`", "SLIs and targets from measured numbers, an error-budget section distinguishing "
             "deliberate `429`/`503` from genuine `5xx`"],
            ["`RUNBOOK.md`", "One entry per alert that actually exists - no speculative entry for an "
             "alert nobody wrote"],
            ["`COST.md`", "Real AWS GPU-rental pricing against a real hosted-API price per token, worked "
             "out as cost-per-million-tokens on both sides after an early draft's unit-conversion error "
             "was caught and fixed"],
            ["`ARCHITECTURE.md`", "Three diagrams (system overview, Argo CD sync-wave ordering, request-"
             "path sequence) and a trust-boundaries table"],
            ["`POSTMORTEM-001.md`", "A blameless write-up of the two chaos-day bugs - what broke, why "
             "nothing caught it sooner, what changed as a result"],
        ],
        widths=[1.5, 5.1],
        size=9.0,
    )
    D.h2("4.4  The new alert chaos day found missing")
    D.p("The VRAM exhaustion experiment (§6) peaked at roughly 95% GPU memory used with no alert firing "
        "- the only GPU alert that existed, `PalisadeGPUSaturated`, watches compute utilisation, not "
        "memory. `PalisadeGPUMemoryPressure` (`>90%` for `5m`) closes that gap, with its own `promtool` "
        "test cases and a runbook entry carrying the WSL2/WDDM caveat §6 found.")


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done")
    _steps(D, [
        ("Load shedding built and unit-tested before the saturation test ran",
         "`InFlightLimiter`'s plain try-acquire/release, wired into both the streaming and non-streaming "
         "paths immediately before the vLLM call, with the budget reservation refunded on every shed - "
         "tested against a saturated limiter, a freed slot letting the next request through, and the "
         "refund path, before a single k6 request hit a real GPU."),
        ("The saturation test run twice, for two different reasons",
         "In CI, against `tests/load/stub_upstream.py` - a dependency-free `http.server` stand-in for "
         "vLLM - because a self-hosted runner on a public repo is a real supply-chain risk this project "
         "already treats seriously (ADR 0025). By hand, against the real RTX 3050, for the numbers that "
         "actually matter: ramping 1 to 30 VUs over 45s, a mixed signal of real rate-limiting and real "
         "load-shedding that took a second look to describe honestly rather than paper over."),
        ("Chaos day run hypothesis-first, against the live cluster, nothing staged",
         "`docs/evidence/m5/chaos-hypotheses.md` written and committed before the first `kubectl delete "
         "pod`. Each of five experiments - kill vLLM mid-stream, stall Redis, lose Redis outright, a "
         "validly signed image from the wrong GitHub Actions workflow, an old but genuinely signed image, "
         "VRAM exhaustion - got its own prediction, its own real command against the real cluster, and "
         "its own evidence file with the raw transcript, not a summary of one."),
        ("Both real bugs fixed, tested, and then verified live a second time after deploying the fix",
         "Unit tests first (`test_upstream_disconnecting_mid_stream_is_a_handled_upstream_error`, "
         "`tests/test_redis_unavailable.py`), then the exact same chaos scenario re-run against the fixed "
         "code once it reached the real cluster - not trusting a green test suite alone to mean the fix "
         "actually works where it matters."),
        ("A second pass found three things the first pass at 'done' had gotten wrong",
         "The VRAM experiment's first write-up concluded vLLM ran in under 120MiB of additional VRAM - "
         "physically impossible for a 1.4GiB checkpoint plus a 512MiB KV-cache reservation, caught before "
         "it went further and corrected with a second, better measurement (§6). The README's status line "
         "claimed 'M5 complete' before the clean-rebuild pass or this document existed - walked back to "
         "an honest status table naming exactly what was and wasn't done yet. And a postmortem draft "
         "mis-cited which file actually carried a corrected claim, caught by checking the citation "
         "against the real file rather than trusting the first draft's memory of where it lived."),
        ("The clean rebuild and the fresh clone, run as two separate, deliberately different tests",
         "`make down && make up && make gitops` proves the chart and config reproduce the running state; "
         "a real `git clone` into an unrelated directory, with its own fresh virtualenv and its own "
         "dependency install, proves the repository itself - not just the cluster's live state - is "
         "complete. Neither test substitutes for the other."),
    ])
    D.h2("5.1  The commands that matter")
    D.code(
        "make down && make up && make gpu-check && make gitops   # clean rebuild, all 6 Apps Synced/Healthy\n"
        "git clone https://github.com/saimcyber/palisade.git /tmp/fresh && cd /tmp/fresh/services/gateway\n"
        "python3 -m venv ~/freshvenv && ~/freshvenv/bin/pip install -q -r requirements-dev.txt\n"
        "~/freshvenv/bin/python -m pytest -q                      # 56 passed, 1 skipped, fresh clone\n"
        "kubectl delete pod -n palisade -l app.kubernetes.io/name=vllm   # chaos experiment 1\n"
        "redis-cli CLIENT PAUSE 8000 ALL                                 # chaos experiment 2")


# =============================================================================
def deep_dive(D):
    D.h1("6. Deep Dive - a VRAM Test That Measured the Wrong Thing, Twice")
    dual(D,
         "A test tried to run the GPU out of memory on purpose, to see whether the platform would crash "
         "cleanly or messily. It never crashed at all - which looked at first like good news, until the "
         "numbers behind that result turned out not to add up, and the real explanation took two more "
         "attempts to actually pin down.",
         "A scratch Pod held an escalating amount of GPU memory (512MiB, then 2.3GiB, then 3.6GiB) with "
         "vLLM scaled to zero, then vLLM was scaled back to 1 to see whether it would fit. It did, every "
         "time - even with `nvidia-smi` reporting only 77MiB free on a 4096MiB card. The first "
         "conclusion - vLLM's real footprint must be far smaller than its ~2.6GiB steady-state figure - "
         "didn't survive a second look: a 1.40GiB checkpoint plus a fixed 512MiB KV-cache reservation "
         "cannot run in under 120MiB of additional dedicated VRAM. `nvidia-smi` was not accounting for "
         "everything using the card.")
    D.h2("What was tried, in order")
    D.table(
        ["Attempt", "Result"],
        [
            ["Escalate the competing allocation until vLLM's restart fails", "It never failed, even at "
             "the card's effective limit - the first, incomplete read: \"this configuration is just more "
             "resilient than expected\""],
            ["Check Windows' own GPU performance counters (`Get-Counter`) for a second memory pool "
             "`nvidia-smi` doesn't report", "Found one: \"Shared Usage\" (host RAM borrowed by the GPU "
             "driver) jumped roughly 2.2GiB at exactly the point Dedicated Usage maxed out"],
            ["Check whether vLLM's own working set moved to that slower pool, or something else did",
             "Decode latency with the competing allocation present (3383ms) vs. without it (3078ms) was "
             "roughly 10% different, not several times slower - if vLLM's actively-read weights had "
             "moved to host RAM, decode would have been far slower than that"],
            ["State the conclusion at the honesty level the evidence actually supports", "The mechanism "
             "is real (Windows backs GPU memory overflow with host RAM rather than failing the "
             "allocation) but *which* allocation moved is not something the available counters can prove "
             "- narrowed the write-up to what was actually measured rather than what seemed most likely"],
        ],
        widths=[2.8, 3.8],
        size=8.8,
    )
    D.p("The hypothesis itself predicted a hard crash (`torch.OutOfMemoryError`, a restart loop) - that "
        "specific prediction was wrong on this host, and plausibly right on a native Linux host, which "
        "was never available to test. The honest finding is narrower than either \"it crashes\" or \"it's "
        "resilient\": on this exact Windows/WSL2/WDDM stack, VRAM exhaustion degrades softly in a way "
        "that is a property of the host, not of this platform's own design - and should not be read as "
        "evidence this configuration tolerates running out of VRAM anywhere else.")
    D.callout("Lesson",
              "A number that doesn't add up is worth more than a conclusion that sounds right. The first "
              "write-up's \"vLLM only needed 120MiB more\" was the more interesting-sounding claim and "
              "the wrong one; the real explanation needed a tool `nvidia-smi` doesn't have "
              "(`Get-Counter`) and a second, independent check (the latency numbers) before it was safe "
              "to write down.", "warn")


# =============================================================================
def deviations(D):
    D.h1("7. Deviations From the Plan")
    D.table(
        ["Plan said", "What was done", "Why"],
        [
            ["Chaos day: \"exhaust VRAM\" implies a crash to recover from", "VRAM exhaustion never "
             "crashed anything on this host - the finding became *why* it didn't, not a recovery story",
             "The real mechanism (a WSL2/WDDM memory-overflow fallback) turned out to be more interesting "
             "and more honest than forcing a crash that this host's driver stack doesn't actually produce"],
            ["(implicit) a chaos finding, once written up, is finished", "The VRAM write-up was revised "
             "twice after its first version - once for a measurement that was physically impossible, "
             "once to narrow an attribution claim the counters couldn't actually support", "Publishing a "
             "wrong conclusion and never revisiting it would be worse than the original mistake"],
            ["(implicit) M5 is 'complete' once chaos day and the docs exist", "The README's status line "
             "briefly claimed exactly that, then was walked back to an explicit status table", "CLAUDE.md's "
             "own definition of 'finished' - the acceptance command passing from a clean rebuild, plus "
             "the milestone document existing - hadn't actually been met yet at that point"],
            ["(not in plan) a stale, empty `observability/` directory from M0's original scaffold",
             "Removed; the real dashboards and alert rules have lived in `deploy/observability/` since "
             "M4 and nothing referenced the old path", "Found while bringing the README's repository "
             "layout up to date - dead scaffolding left over three milestones is worth deleting, not "
             "documenting around"],
        ],
        widths=[1.9, 2.3, 2.4],
        size=8.8,
    )


# =============================================================================
def tool_choices(D):
    D.h1("8. Tool Choices - and What Was Rejected")
    D.table(
        ["Chose", "Over", "Because"],
        [
            ["**A plain `int` counter**", "`asyncio.Semaphore`, or a Redis-backed limit",
             "Single-threaded cooperative asyncio has no race between a check and an increment with no "
             "`await` between them - anything heavier is complexity this specific concurrency model "
             "doesn't need (ADR 0024)"],
            ["**k6 in CI against a stub, real GPU runs by hand**", "A self-hosted GitHub Actions runner",
             "A fork's PR running arbitrary code on the machine holding this project's cosign signing "
             "material is a real supply-chain risk on a public repo, not a hypothetical one (ADR 0025)"],
            ["Writing every chaos hypothesis before running the experiment", "Running the experiment "
             "first and describing the result afterward", "A hypothesis adjusted after the fact isn't "
             "evidence of anything except what you already believed"],
            ["`oras copy -r` for copying a real signature between repositories", "The deprecated `cosign "
             "copy`", "`cosign copy` silently copied only the raw image manifests, not the actual "
             "Sigstore bundle referrers - confirmed by a `cosign verify` immediately failing; `oras`'s "
             "explicit referrers-aware copy carried the real signature correctly"],
            ["Windows' `Get-Counter` GPU adapter-memory counters", "Trusting `nvidia-smi` alone",
             "`nvidia-smi` only ever reports one of two memory pools the WDDM driver actually uses; the "
             "VRAM chaos finding (§6) does not exist without the second counter"],
        ],
        widths=[1.9, 2.1, 2.6],
        size=8.8,
    )


# =============================================================================
def limitations(D):
    D.h1("9. Limitations")
    D.p("What this setup genuinely cannot do, stated plainly.")
    D.table(
        ["Limitation", "Why it exists / what would fix it"],
        [
            ["No GPU memory alert existed until chaos day found the gap",
             "`PalisadeGPUMemoryPressure` closes it now, but the fact it was missing for two whole "
             "milestones is itself a limitation of the review process that should have caught it sooner"],
            ["The VRAM chaos finding's mechanism is inferred, not directly observed",
             "Windows' GPU adapter-memory counters report the whole adapter, not a specific process - "
             "there is no counter available here that can prove *which* allocation moved to host RAM, "
             "only that something did"],
            ["The VRAM finding was never reproduced on native Linux",
             "No such host was available to this project; the soft-degradation behavior is plausibly "
             "specific to this host's WSL2/WDDM driver stack and should not be assumed to hold elsewhere"],
            ["Redis's own periodic snapshotting means a restart doesn't always reset tenant state",
             "Only a genuine Pod reschedule, not a same-Pod container restart, is guaranteed to produce "
             "an empty store - documented precisely in `redis-deployment.yaml` and M4's limitations table "
             "after chaos day found the original wording was imprecise"],
            ["The Cloudflare Tunnel demo and the short demo video are both still open",
             "The Tunnel needs a public-surface action (a registry/tunnel endpoint) that this session's "
             "own permission boundaries hand to the operator rather than complete unattended; the video "
             "is explicitly deferred by choice, not forgotten"],
        ],
        widths=[2.6, 4.0],
        size=9.0,
    )


# =============================================================================
def mistakes(D):
    D.h1("10. Mistakes and What They Taught")
    D.table(
        ["Mistake", "Lesson"],
        [
            ["Concluded vLLM ran in under 120MiB of additional VRAM from a single `nvidia-smi` reading",
             "A number that contradicts known physical facts (a 1.4GiB checkpoint, a 512MiB fixed "
             "reservation) is a sign the measurement is incomplete, not a sign the system is unusually "
             "efficient - check for a second data source before writing the surprising conclusion down"],
            ["An edit meant for the streaming handler landed in a different function first, since all "
             "three upstream-calling functions had near-identical exception-handling blocks",
             "Caught only by re-running the regression test and seeing the exact original failure symptom "
             "persist - a fix isn't verified by writing it, it's verified by the test that was supposed "
             "to fail actually passing afterward"],
            ["Restarted Prometheus once right after updating its ConfigMap and assumed the new alert "
             "rule would be there", "The kubelet's local ConfigMap cache can lag the API server's "
             "committed value even for a pod that didn't exist at update time - confirmed the file on "
             "disk was already correct while the loaded rule set was still stale; a second restart picked "
             "up the real content. Documented in `prometheus-config.yaml`'s own header for the next "
             "person who hits it"],
            ["Published the README's 'M5 complete' status line before the clean-rebuild pass or this "
             "document existed", "A status claim should point at evidence that already exists, not at "
             "work still in flight - walked back to an explicit table naming exactly what was done and "
             "what wasn't, which turned out to be more useful than the confident version anyway"],
        ],
        widths=[2.9, 3.7],
        size=9.0,
    )


# =============================================================================
def explain(D):
    D.h1("11. Design Rationale - Questions Answered")
    _qa(D, [
        ("Why write every chaos hypothesis down before running anything?",
         "Because a prediction written after the result is just a story that happens to match - the "
         "value of chaos testing is specifically in finding out where your mental model of the system "
         "is wrong, and that only shows up if the prediction is locked in first."),
        ("Why does a cache hit still bill the tenant, and why does load shedding refund the reservation?",
         "Both exist for the same reason in opposite directions: the platform's numbers have to reflect "
         "what actually happened. A cache hit is still real usage a customer would expect to see on a "
         "bill; a shed request never reached the GPU at all, so charging for it would be billing for work "
         "that was never done."),
        ("Why keep publishing a finding that turned out to be wrong, instead of just fixing it quietly?",
         "Because the wrong first conclusion and the process of finding out it was wrong are both real "
         "engineering content - a document that only shows the final, correct answer teaches a reader "
         "nothing about how to catch the same mistake themselves."),
        ("Why does the VRAM chaos finding hedge so much about what actually moved to host RAM?",
         "Because the honest answer is that the available tooling cannot fully prove it. Claiming more "
         "certainty than the evidence supports is a worse failure than admitting the limit of what was "
         "actually measured."),
        ("What would you change starting over?",
         "Check a surprising number against the physical facts it implies before writing the conclusion "
         "down, not after. 'vLLM uses almost no extra memory' should have been checked against 'a "
         "1.4GiB checkpoint has to go somewhere' in the same sitting it was first observed, not in a "
         "follow-up pass."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("12. Glossary - Terms Introduced in M5")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**Load shedding**", "Deliberately rejecting a request before it reaches an overloaded "
             "dependency, instead of letting it queue indefinitely or fail unpredictably"],
            ["**Chaos day / chaos testing**", "Deliberately breaking a live system on purpose, under "
             "controlled conditions, to find failure modes before an untested one finds you some other way"],
            ["**Blameless postmortem**", "A write-up of a real failure that focuses on the mechanism that "
             "allowed it, not on who wrote the original code"],
            ["**SLO / SLI**", "A Service Level Objective is the target; a Service Level Indicator is the "
             "measured number compared against it"],
            ["**Error budget**", "How much a system is allowed to fail against its SLO before that "
             "failure counts as a real incident rather than expected, deliberate behaviour (like a "
             "designed `429` or `503`)"],
            ["**WDDM**", "Windows Display Driver Model - the Windows graphics driver stack a WSL2 host's "
             "GPU access runs through, with its own memory-management behaviour distinct from native "
             "Linux's NVIDIA driver"],
            ["**OCI referrers**", "A standard way to attach extra artifacts (like a cosign signature) to "
             "an image in a registry, keyed to its exact digest"],
        ],
        widths=[1.7, 4.9],
        size=9.0,
    )
    D.h1("13. Open Items Going Into What's Next")
    D.table(
        ["Item", "Action"],
        [
            ["Cloudflare Tunnel demo", "Set up a public-surface endpoint for a tightly-capped demo tenant"],
            ["Short demo video", "Deliberately deferred by choice, not forgotten"],
            ["No Alertmanager receiver (carried from M4)", "Wire one once there's a real notification "
             "channel to use"],
            ["VRAM soft-degradation mechanism never confirmed on native Linux", "Would need a non-WSL2 "
             "host this project doesn't currently have access to"],
        ],
        widths=[2.6, 4.0],
        size=9.0,
    )
    D.spacer(4)
    D.callout("Where this goes",
              "The infrastructure and the proof both exist now: a working platform, a load test that "
              "found its real ceiling, a chaos day that found and fixed two bugs nothing else would have "
              "caught, and five documents that let a stranger understand all of it without a guided "
              "tour. What's left is making it reachable - a public demo link, and the few minutes of "
              "video that show it working.", "ok")
