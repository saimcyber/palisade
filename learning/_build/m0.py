# -*- coding: utf-8 -*-
"""Content for the M0 learning document."""
from docx_kit import *   # noqa: F403


# --- a device used throughout: the same idea said twice ----------------------
def dual(D, plain, technical):
    """Render a 'plain language' / 'technically' pair."""
    t = D.d.add_table(rows=2, cols=2)
    t.style = "Table Grid"
    for row, (label, body, fill) in enumerate((
            ("IN PLAIN LANGUAGE", plain, "EAF3F4"),
            ("TECHNICALLY", technical, "F4F5F7"))):
        lab, txt = t.rows[row].cells
        lab.width = Inches(1.25); txt.width = Inches(5.35)
        shade_cell(lab, fill); shade_cell(txt, fill)
        lab.text = ""; txt.text = ""
        p = lab.paragraphs[0]; no_space(p, 3, 3)
        r = p.add_run(label)
        r.bold = True; r.font.size = Pt(7.8); r.font.name = BODY_FONT
        r.font.color.rgb = TEAL if row == 0 else SLATE
        p2 = txt.paragraphs[0]; no_space(p2, 3, 3)
        add_rich(p2, body, size=10)
    set_col_widths(t, [1.25, 5.35])
    D.d.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def cover(D):
    d = D.d
    t = d.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade_cell(c, F_COVER); c.text = ""
    p = c.paragraphs[0]; no_space(p, 22, 2)
    r = p.add_run("PALISADE")
    r.bold = True; r.font.size = Pt(26); r.font.name = BODY_FONT; r.font.color.rgb = WHITE
    p2 = c.add_paragraph(); no_space(p2, 2, 2)
    r = p2.add_run("Learning Log  ·  Milestone M0")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 20)
    r = p3.add_run("Foundations: a GPU-capable Kubernetes cluster on a laptop")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(10)
    D.p("WHAT THIS DOCUMENT IS", size=9.5, bold=True, color=SLATE, after=2)
    D.p("A record of everything done in Milestone M0: what was built, how, what went wrong, "
        "what was decided differently from the original plan, why each tool was chosen over its "
        "alternatives, and what this setup cannot do. Every idea is given twice - once in plain "
        "language, once technically.", after=10)

    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M0 - Foundations** (Day 1 of 20)"],
            ["Date completed", "6 September 2026"],
            ["Goal", "`make up` produces a local Kubernetes cluster in which a scheduled pod can use the GPU"],
            ["Result", "**Passed.** 28/28 environment checks, verified from a clean teardown and rebuild"],
            ["Hardware", "NVIDIA RTX 3050 Laptop (4 GB VRAM), 16 GB RAM, 12 logical CPUs, Windows 11 + WSL2"],
            ["Repo location", "`~/palisade` inside WSL2 Ubuntu 24.04 (installed on the E: drive)"],
            ["Commits", "`4bc20fc` repo skeleton · `0c8ae65` GPU-capable cluster via CDI"],
            ["Time cost", "Roughly one working day, of which the GPU problem was the majority"],
        ],
        widths=[1.5, 5.1],
    )
    D.callout("The one thing to take away from M0",
              "The GPU refused to reach a pod **three times, for three unrelated reasons.** Diagnosing "
              "those three failures taught more than the rest of the milestone combined, and the write-up "
              "in Section 5 is the single most interview-valuable thing produced so far. A milestone that "
              "goes smoothly teaches you almost nothing.", "ok")


def what_m0_was_for(D):
    D.h1("1. What M0 Was For")

    D.h2("1.1  The goal, stated simply")
    dual(D,
         "Before building anything clever, prove the hardest physical thing works: that a **graphics card "
         "in a laptop** can actually be used by a program that Kubernetes starts. If that fails, the whole "
         "project design has to change - so it is tested first, on day one, before a single line of "
         "application code exists.",
         "Verify the full device path `Windows driver -> WSL2 -> Docker -> k3d node container -> containerd "
         "-> pod`, then codify it in `scripts/cluster-up.sh` so `make up` reproduces it deterministically.")

    D.h2("1.2  Why this is done first")
    D.p("Everything else in Palisade - the gateway, the CI pipeline, the policies, the dashboards - is "
        "**portable and low-risk**. It would work on any machine. GPU passthrough is the only part that "
        "depends on this specific laptop, this specific driver, and this specific virtualisation stack. "
        "It is therefore the only task that could force the architecture to change.")
    D.callout("The principle worth naming",
              "**Sequence work by risk, not by convenience.** The most uncertain dependency goes first, "
              "with a time limit and a pre-agreed fallback. Doing the easy parts first feels productive "
              "and hides the thing that can kill the project until you have spent two weeks on it.", "note")

    D.h2("1.3  The five tasks")
    D.table(
        ["#", "Task", "Outcome"],
        [
            ["0.1", "Verify the GPU end to end", "**Done** - and it took three attempts (Section 5)"],
            ["0.2", "Install the toolchain, add `make doctor`", "**Done** - 15 pinned tools, 28 checks"],
            ["0.3", "Repo skeleton, Makefile, licence, pre-commit", "**Done** - 31 files, 2 commits"],
            ["0.4", "Cluster profiles (`up-lite` / `up-full`)", "**Done** - RAM-constrained by design"],
            ["0.5", "Cap WSL2 memory", "**Done** - 10 GB cap, 8 CPUs, swap on E:"],
        ],
        widths=[0.4, 3.0, 3.2],
    )


def starting_point(D):
    D.h1("2. What the Machine Looked Like Before")
    D.p("The plan assumed a working WSL2 + Docker setup with an untested GPU. Reality differed in three "
        "ways that mattered, and finding them **before** installing anything saved a lot of rework.")

    D.table(
        ["What was checked", "What was found", "Why it mattered"],
        [
            ["GPU", "RTX 3050 Laptop, **4 GB VRAM**, driver 616.64",
             "4 GB confirms the model choice: Qwen2.5-0.5B, not something larger. Sizing the model to the "
             "hardware is a decision, not a compromise."],
            ["WSL distros", "**None.** Only Docker Desktop's internal `docker-desktop` distro",
             "There was no Linux to work in at all. A full Ubuntu install had to be added to the milestone."],
            ["Docker Desktop", "Installed (4.86.0) and previously used",
             "It had a **19.9 GB data disk on D:**, with real content including a live Supabase stack."],
            ["C: drive", "**4.6 GB free** (later 1.4 GB)",
             "Dangerously low. Windows itself needs headroom, and nothing new could be installed there."],
            ["D: drive", "12.5 GB free, holding Docker's data",
             "Too small for vLLM's ~10 GB image, which lands in M1."],
            ["E: drive", "102 GB free",
             "The only viable home for WSL, Docker data and model weights."],
            ["RAM", "15.2 GB total",
             "Forced the `up-lite` / `up-full` profile split - the full stack will not fit alongside a GPU workload."],
        ],
        widths=[1.15, 2.15, 3.3],
    )

    D.callout("A judgement call worth recording",
              "Docker's existing data disk contained **11 running containers belonging to an unrelated, "
              "active project** (a Supabase stack). The tempting move - wipe Docker and start clean - would "
              "have destroyed someone's working database. Nothing was deleted without asking, and even then "
              "only genuinely dead artefacts (5-month-old minikube images, build cache) were removed. "
              "**Read the inventory before you clean.**", "warn")


def decisions(D):
    D.h1("3. Decisions Taken Before Writing Any Code")
    D.p("Four decisions were made up front because each one would have been expensive to reverse later. "
        "Each is recorded with the alternatives that were rejected.")

    # --- 1
    D.h2("3.1  Develop inside WSL2 Ubuntu, not on Windows")
    dual(D,
         "Work inside a real Linux system running on the Windows machine, rather than using Windows tools "
         "directly. Almost every tool in this project was built for Linux first, and the servers this "
         "project imitates all run Linux.",
         "Install Ubuntu 24.04 as a WSL2 distribution and treat it as the development host. Docker Desktop "
         "exposes its daemon into the distro through WSL integration, so containers, k3d and the GPU are "
         "all reachable natively.")
    D.table(
        ["Option", "Verdict"],
        [
            ["**WSL2 Ubuntu** (chosen)",
             "Native Linux tooling, correct file permissions, matches what a real deployment looks like, "
             "and GPU passthrough is supported."],
            ["Windows tooling directly",
             "Rejected. Most tools have Windows builds, but shell scripting, Makefiles and file permissions "
             "become a constant source of friction - and the portfolio value of 'I did this on Linux' is lost."],
            ["A virtual machine (VirtualBox/Hyper-V)",
             "Rejected. Heavier on a 16 GB machine, and GPU passthrough into a conventional VM is far harder "
             "than WSL2's built-in support."],
            ["Dual-boot Linux",
             "Rejected as too disruptive, though it is genuinely the simplest technical path and remains a "
             "reasonable future move."],
        ],
        widths=[1.75, 4.85],
    )

    # --- 2
    D.h2("3.2  Put everything on the E: drive")
    dual(D,
         "The main Windows drive was nearly full, so Linux and all its large files were installed on the "
         "spare drive with 100 GB free.",
         "Ubuntu installed with `wsl --install --location E:\\WSL\\Ubuntu`, and the WSL swap file placed at "
         "`E:\\WSL\\swap.vhdx` via `.wslconfig`. Docker's data disk still needs relocating from D: to E: - "
         "the one open item from M0.")
    D.callout("Limitation found here",
              "Docker Desktop's disk image location **cannot be changed reliably from the command line.** "
              "Editing `settings-store.json` directly was attempted: Docker accepted and preserved the keys, "
              "but did not perform the migration. The vendor-supported path is the GUI "
              "(Settings > Resources > Advanced), which triggers Docker's own move routine. This is a real "
              "automation gap, not an oversight.", "warn")

    # --- 3
    D.h2("3.3  Keep the repository inside the Linux filesystem")
    dual(D,
         "The project's code lives inside Linux's own storage rather than on the Windows drive, because "
         "reaching across from Linux to Windows files is slow and loses information about file permissions.",
         "The repo is at `~/palisade` on ext4 inside the WSL2 VM, not on `/mnt/e`. The Windows drive is "
         "mounted through the 9p/DrvFs protocol, which is markedly slower for many small files and does not "
         "honour Unix permission bits - which matters for the `age` private keys, cosign material and "
         "executable script bits used from M2 onward.")
    D.p("Accessible from Windows at `\\\\wsl$\\Ubuntu-24.04\\home\\saim\\palisade` when needed, and pushed "
        "to GitHub regardless, so nothing is trapped.")

    # --- 4
    D.h2("3.4  Pin every tool version, and verify the pins exist")
    dual(D,
         "Every tool is installed at an exact version written down in a script, not 'whatever is newest "
         "today'. Otherwise the setup quietly changes underneath you and breaks for reasons you cannot trace.",
         "`scripts/install-tools.sh` declares an explicit version constant per tool and compares it against "
         "the installed binary, reinstalling only on mismatch. This makes the script idempotent **and** an "
         "upgrade mechanism.")
    D.callout("A mistake made and corrected here",
              "The first version of the installer used pins that were **all significantly out of date** - "
              "Helm 3.16 when 4.2.4 is current, k6 0.55 against 2.2.0, and a Trivy version that never "
              "existed, which failed with a 404. The fix was to query each project's release API and verify "
              "every download URL returned HTTP 200 *before* rewriting the script. **Never pin a version you "
              "have not confirmed exists.**", "danger")


def what_was_built(D):
    D.h1("4. What Was Actually Built")

    D.h2("4.1  The environment")
    D.table(
        ["Layer", "What was done", "Detail"],
        [
            ["WSL2 config", "Wrote `%USERPROFILE%\\.wslconfig`",
             "10 GB RAM cap, 8 of 12 CPUs, 4 GB swap on E:, `autoMemoryReclaim=gradual`"],
            ["Distro", "Installed Ubuntu 24.04.4 LTS to E:",
             "`wsl --install Ubuntu-24.04 --location E:\\WSL\\Ubuntu --no-launch`"],
            ["User", "Created `saim` non-interactively",
             "sudo + adm groups, **locked password** with passwordless sudo, systemd enabled via `/etc/wsl.conf`"],
            ["Docker", "Enabled WSL integration",
             "Injected `/usr/bin/docker`; required a distro restart to wire the socket"],
        ],
        widths=[1.05, 1.95, 3.6],
    )
    D.callout("Why the user has a locked password rather than a weak one",
              "Creating the account non-interactively needed *some* password decision. Setting a guessable "
              "one and writing it into a transcript would be worse than useless. Instead the password is "
              "locked outright and `sudo` is passwordless - WSL logs the default user in directly, so no "
              "password is ever needed, and there is no weak credential to leak. **The most secure "
              "credential is the one that does not exist.**", "ok")

    D.h2("4.2  The repository")
    D.code("""palisade/
+-- Makefile                 one entry point for every operation
+-- scripts/
|   +-- install-tools.sh     pinned, version-aware, idempotent toolchain installer
|   +-- doctor.sh            28 environment checks; exits non-zero so CI can gate on it
|   +-- build-k3s-image.sh   builds the GPU-capable node image
|   +-- cluster-up.sh        creates the cluster; branches WSL2 vs native Linux
|   +-- setup-gpu-cdi.sh     the GPU fix (Section 5)
|   +-- cluster-down.sh      teardown, with --purge
+-- docker/k3s-nvidia/       Dockerfile for the custom k3s node image
+-- k8s/gpu-check.yaml       the M0 acceptance test, as a Job
+-- docs/adr/                0001 record decisions - 0002 the GPU investigation
+-- learning/                this document
+-- services/ infra/ deploy/ observability/ tests/    (scaffolded, filled from M1)""", size=8.0)

    D.h2("4.3  The toolchain")
    D.p("Fifteen tools, every one pinned and verified against upstream before being written into the script:")
    D.table(
        ["Tool", "Version", "What it is for"],
        [
            ["kubectl", "1.36.4", "Talk to Kubernetes. Matched to the k3s minor version deliberately."],
            ["helm", "4.2.4", "Install packaged Kubernetes applications."],
            ["k3d", "5.9.0", "Run a Kubernetes cluster inside Docker containers."],
            ["terraform", "1.16.1", "Infrastructure as code - AWS and cluster add-ons (M2)."],
            ["k6", "2.2.0", "Load testing (M5)."],
            ["cosign", "3.1.3", "Sign and verify container images (M2)."],
            ["syft", "1.51.1", "Generate a software bill of materials (M2)."],
            ["trivy", "0.74.0", "Scan images for known vulnerabilities (M2)."],
            ["sops + age", "3.13.3 / 1.1.1", "Encrypt secrets so they can live safely in Git (M3)."],
            ["argocd", "3.5.2", "GitOps - make the cluster match the repo (M3)."],
            ["kustomize", "5.8.1", "Template-free Kubernetes configuration."],
            ["yq / jq", "4.53.6 / 1.7", "Query and edit YAML and JSON in scripts."],
            ["aws-cli", "2.36.40", "AWS access via OIDC (M2)."],
            ["pre-commit, ruff", "latest", "Lint and format on every commit."],
        ],
        widths=[1.15, 1.1, 4.35],
    )
    D.callout("A trap worth knowing about: Windows programs shadowing Linux ones",
              "`aws` initially resolved to a **Windows** Python script at `/mnt/c/...` that cannot execute "
              "under Linux. WSL appends the Windows PATH by default, so Windows executables appear inside "
              "Linux and silently win when no Linux equivalent exists. The installer was changed to test for "
              "a real binary at `/usr/local/bin/aws` rather than trusting `command -v`. A verification step "
              "was then added that prints the resolved path of every tool and flags anything under `/mnt/`.",
              "warn")


def gpu_problem(D):
    D.h1("5. The GPU Problem - Three Failures")
    D.p("This is the substance of M0. The GPU worked at every layer until the very last one, and then "
        "failed three times for three unrelated reasons. Each failure is worth understanding on its own.",
        color=SLATE)

    D.h2("5.1  What already worked")
    D.table(
        ["Check", "Result"],
        [
            ["`nvidia-smi` in Windows", "RTX 3050, driver 616.64"],
            ["`nvidia-smi` inside WSL2 Ubuntu", "works"],
            ["`docker run --gpus all ... nvidia-smi`", "works"],
            ["`docker exec <k3d-node> nvidia-smi`", "works"],
            ["`nvidia-container-cli info` inside the node", "detects the RTX 3050 correctly"],
            ["**A pod started by Kubernetes**", "**failed**"],
        ],
        widths=[3.3, 3.3],
    )
    D.p("Everything up to the final boundary was fine. That narrowed the problem enormously: the GPU was "
        "reaching the node container, but not being handed on to containers *inside* it.")

    # ---------- failure 1
    D.h2("5.2  Failure 1 - Helm said success and deployed nothing")
    dual(D,
         "The standard tool for sharing a GPU with Kubernetes was installed, and the installer reported "
         "success. But it had not actually started anything - it had been told to run on machines carrying "
         "a particular label, and no machine had that label. So it ran on zero machines and reported no error.",
         "The `nvidia-device-plugin` chart carries a default `nodeAffinity` requiring one of "
         "`feature.node.kubernetes.io/pci-10de.present`, "
         "`feature.node.kubernetes.io/cpu-model.vendor_id=NVIDIA`, or `nvidia.com/gpu.present`. Those labels "
         "are applied by NVIDIA's Node Feature Discovery, which was disabled (`gfd.enabled=false`) to save "
         "memory. The DaemonSet was created correctly and matched no nodes: `DESIRED = 0`.")
    D.callout("Lesson 1",
              "**A successful `helm install` means the objects were created, not that anything is running.** "
              "`--wait` waits for what exists; if a DaemonSet wants zero pods, zero pods is a satisfied "
              "state. Always check `DESIRED`, never the exit code alone.", "danger")
    D.p("**Fix:** label the node by hand - `kubectl label node --all nvidia.com/gpu.present=true`. This is "
        "now done automatically in `cluster-up.sh` on the native-Linux path, with a comment explaining why.")

    # ---------- failure 2
    D.h2("5.3  Failure 2 - NVML is not supported on WSL2")
    D.p("With scheduling fixed, the plugin started and immediately crash-looped:")
    D.code("""E  Failed to initialize NVML: Not Supported
E  If this is a GPU node, did you set the docker default runtime to `nvidia`?
E  error starting plugins: ... nvml init failed: Not Supported""", size=8.5)
    dual(D,
         "The tool asks the graphics driver to introduce itself using a standard interface. On Windows "
         "running Linux inside it, the graphics card is not presented in the normal way - it is a special "
         "shared device - and that standard interface simply does not exist. No setting fixes this.",
         "The device plugin enumerates GPUs through **NVML**. Under WSL2 the GPU is exposed as `/dev/dxg`, a "
         "paravirtualised interface, with the real driver on the Windows side. NVML has no support for this "
         "model. The device plugin **cannot work under WSL2** - this is architectural, not configuration.")
    D.callout("Lesson 2",
              "**Know the difference between 'misconfigured' and 'impossible'.** Time spent tuning a "
              "component that cannot work in your environment is time wasted. Recognising the second "
              "category quickly is what kept this within its half-day budget.", "danger")

    # ---------- the alternative
    D.h2("5.4  The alternative: CDI")
    dual(D,
         "Instead of asking the driver to introduce itself, write down an explicit list: these device files "
         "and these library files must be copied into the container. A helper tool can generate that list "
         "by inspecting the machine.",
         "**CDI (Container Device Interface)** is a vendor-neutral standard for describing device injection. "
         "`nvidia-ctk cdi generate` detects WSL, locates the Windows driver store mounted into the VM, and "
         "writes `/etc/cdi/nvidia.yaml` listing the device nodes, mounts and hooks containerd should apply.")
    D.code("""Auto-detected mode as 'wsl'
Selecting /dev/dxg as /dev/dxg
Using WSL driver store path: /usr/lib/wsl/drivers/nvlti.inf_amd64_...""", size=8.5)

    # ---------- failure 3
    D.h2("5.5  Failure 3 - one warning line was the entire problem")
    D.p("With the CDI spec generated, the pod **still** failed - but with a different message:")
    D.code("""Failed to initialize NVML: N/A        <-- not "Not Supported" this time""", size=8.5)
    D.callout("The diagnostic insight",
              "`Not Supported` and `N/A` come from the same function and mean completely different things. "
              "`Not Supported` meant NVML could not work at all. `N/A` meant `nvidia-smi` was present and "
              "running but could not reach the driver - which proved injection was now **partially** "
              "working. **Error text is a fingerprint. Read it precisely.**", "note")
    D.p("The cause was one warning among forty lines of generation output:")
    D.code("""warning: Could not locate libdxcore.so: libdxcore.so: not found""", size=8.5)
    dual(D,
         "The generated list was missing one essential library. The tool looked for it in one folder, but "
         "Docker had placed it in a different one. It warned and carried on, producing a list that included "
         "the program but not the library the program needs to work.",
         "`nvidia-ctk` searches the WSL driver store for `libdxcore.so`; Docker Desktop places it in "
         "`/usr/lib/x86_64-linux-gnu/`. Generation warned and continued, emitting a spec that mounted "
         "`nvidia-smi` and `libnvidia-ml.so.1` but not `libdxcore.so`, which both depend on. Appending the "
         "missing mount to the spec resolved it immediately.")
    D.callout("Lesson 3",
              "**Warnings are not decoration.** A tool that warns and continues will hand you a "
              "plausible-looking artefact with a hole in it. This one line was the difference between a "
              "working cluster and a day of confusion.", "danger")

    D.h2("5.6  The result")
    D.code("""+-----------------------------------------------------------------------------+
| NVIDIA-SMI 615.65.07       KMD Version: 616.64     CUDA UMD Version: 13.4   |
|   0  NVIDIA GeForce RTX 3050 ...  On  |  0MiB / 4096MiB  |  0%   Default    |
+-----------------------------------------------------------------------------+
GPU 0: NVIDIA GeForce RTX 3050 Laptop GPU (UUID: GPU-6d9e8048-...)

PASS: the scheduler placed this pod and it can drive the GPU.
M0 ACCEPTANCE PASSED""", size=8.0)
    D.p("Verified from a **complete teardown and rebuild**, not from the already-working cluster. That "
        "distinction matters: it proves the automation works, not merely that the machine happens to be in "
        "a good state.")


def deviations(D):
    D.h1("6. Where This Deviated From the Plan, and Why")
    D.p("Six departures from the written plan. Each was a response to something the plan could not have "
        "known, and each is recorded rather than quietly absorbed.")

    D.table(
        ["#", "The plan said", "What was done instead", "Why"],
        [
            ["1", "WSL2 and Docker are working; GPU untested",
             "Installed Ubuntu 24.04 from scratch",
             "There was **no Linux distro at all** - only Docker's internal one. The plan's premise was wrong."],
            ["2", "Use the NVIDIA device plugin so pods request `nvidia.com/gpu`",
             "Use **CDI injection** on WSL2; keep the device plugin for native Linux",
             "The device plugin cannot function under WSL2 (Section 5.3). Branching on host keeps the repo "
             "portable and makes the difference explicit."],
            ["3", "Install the listed toolchain",
             "Verified every version against upstream release APIs first",
             "The original pins were badly out of date and one did not exist. Verification is now part of the process."],
            ["4", "k3s v1.31.5, CUDA 12.4",
             "k3s v1.36.4, CUDA 12.8, Helm 4",
             "Current versions. A portfolio project running two-year-old components invites an awkward question."],
            ["5", "Nothing about existing machine state",
             "Audited Docker contents; deleted only what was approved",
             "The machine held an active Supabase project. Destroying it would have been unacceptable."],
            ["6", "Nothing about C: drive",
             "Reclaimed 3.4 GB of caches",
             "C: had fallen to **1.4 GB free**, which risks Windows stability and blocks tooling."],
        ],
        widths=[0.3, 1.55, 1.8, 2.95],
    )

    D.callout("A deviation that is worth more than the original plan",
              "Deviation 2 turned a routine 'install the standard plugin' step into a genuine investigation "
              "with a written ADR. **When an interviewer asks about a hard problem you solved, this is the "
              "answer** - and it only exists because the environment refused to cooperate. Do not smooth "
              "these out of the record.", "ok")


def tool_choices(D):
    D.h1("7. Tool Choices: What Was Picked and What Was Rejected")
    D.p("In an interview the reasoning matters more than the selection. Each row is a decision you should "
        "be able to defend in two sentences.")

    D.table(
        ["Decision", "Chosen", "Rejected, and why"],
        [
            ["Local Kubernetes", "**k3d** (k3s in Docker)",
             "**minikube** - heavier, and its GPU story on WSL2 is no better. **kind** - viable, but k3d "
             "gives a real k3s distribution matching what small companies actually run. **Docker Desktop's "
             "built-in Kubernetes** - no control over the node image, which this project needs."],
            ["GPU into pods", "**CDI**",
             "**NVIDIA device plugin** - architecturally impossible on WSL2. **Privileged pods with manual "
             "device mounts** - would work, but is a security anti-pattern in a project whose entire theme "
             "is security."],
            ["Node image", "**Custom k3s + nvidia-container-toolkit**",
             "**Stock `rancher/k3s`** - contains no NVIDIA runtime, so containerd inside the node cannot "
             "pass the GPU on, even though the node itself can see it."],
            ["Secrets (from M3)", "**SOPS + age**",
             "**HashiCorp Vault** - roughly 1 GB of RAM for capability SOPS already provides, and it sits "
             "outside the GitOps model rather than inside it. **Sealed Secrets** - viable, but SOPS keeps "
             "files readable and reviewable in Git."],
            ["Task runner", "**Make**",
             "**Shell scripts alone** - no discoverability. **Taskfile/just** - nicer, but Make is present "
             "everywhere and is what a reviewer expects."],
            ["Version strategy", "**Exact pins with verification**",
             "**`latest` tags** - not reproducible; the setup changes underneath you. **Distro packages** - "
             "usually years out of date."],
            ["Doc format", "**Markdown ADRs in the repo**",
             "**A wiki or external doc** - decisions must live beside the code they explain, and be "
             "reviewable in the same pull request."],
        ],
        widths=[1.05, 1.5, 4.05],
    )


def limitations(D):
    D.h1("8. Limitations of This Setup")
    D.p("Being able to state what your system *cannot* do is a stronger signal than claiming it does "
        "everything. These are real and should be said out loud in interviews.")

    D.table(
        ["Limitation", "What it means in practice", "Mitigation / honest position"],
        [
            ["**No scheduler-level GPU accounting**",
             "Nothing requests `nvidia.com/gpu`, so Kubernetes does not know the GPU exists and would "
             "happily place two GPU pods on the same node.",
             "With one GPU and one vLLM replica it does not bite. It also reinforces a decision taken "
             "independently: Palisade does not autoscale the model tier, it does admission control and load "
             "shedding at the gateway."],
            ["**4 GB of VRAM**",
             "Only small models fit. Qwen2.5-0.5B in fp16 is about 1 GB of weights plus KV cache.",
             "Deliberate, and irrelevant to the DevOps story - the model is one Helm value. Everything of "
             "value sits in front of it and is model-agnostic."],
            ["**10 GB for the whole Linux side**",
             "Argo CD, Prometheus, Grafana and a GPU workload cannot all run at once.",
             "The `up-lite` / `up-full` profile split. Turning off what you are not working on is a real "
             "operational decision on constrained hardware."],
            ["**Single node**",
             "No multi-node scheduling, no real node failure testing, no topology spread.",
             "Out of scope. Chaos testing in M5 targets pod and dependency failure instead."],
            ["**CDI spec is generated at runtime**",
             "It cannot be baked into the node image, because the WSL driver store path is host-specific.",
             "`cluster-up.sh` regenerates it on every cluster creation, so it is reproducible even though it "
             "is not static."],
            ["**Docker's disk location needs a GUI step**",
             "The one part of the environment that is not scripted.",
             "Documented explicitly rather than hidden. Vendor limitation, not an oversight."],
            ["**The `nvidia` RuntimeClass appears late**",
             "k3s creates it a few seconds after the node reports Ready.",
             "Found during rebuild testing and fixed with a wait loop - a race that only appears when you "
             "test from scratch rather than incrementally."],
        ],
        widths=[1.5, 2.4, 2.7],
    )


def explain(D):
    D.h1("9. What You Should Be Able to Explain")
    D.p("If you can answer these without notes, M0 has done its job.")
    qs = [
        ("Why did you test the GPU before writing any code?",
         "Because it was the only part of the design that could force an architecture change. Everything "
         "else is portable. I sequenced the work by risk and gave it a half-day time box with a documented "
         "fallback - running vLLM as an external backend outside the cluster."),
        ("Why can't you use the NVIDIA device plugin?",
         "It discovers GPUs through NVML. Under WSL2 the GPU is exposed as `/dev/dxg`, a paravirtualised "
         "device with the real driver on the Windows side, and NVML does not support that model. It is not a "
         "configuration problem - the component cannot work there. I use CDI instead, and the repo still "
         "uses the device plugin on native Linux."),
        ("What is CDI?",
         "The Container Device Interface - a vendor-neutral standard describing how to inject a device into "
         "a container: which device nodes, which library mounts, which hooks. Rather than the runtime asking "
         "a driver to enumerate hardware, it reads an explicit specification."),
        ("You said Helm reported success but nothing ran. How?",
         "The chart created a DaemonSet whose node affinity required a label from NVIDIA's Feature "
         "Discovery, which I had disabled to save memory. The DaemonSet matched zero nodes, so `DESIRED=0`. "
         "That is a satisfied state, so `--wait` returned cleanly. It taught me to check `DESIRED`, not the "
         "exit code."),
        ("How did you find the libdxcore.so problem?",
         "By reading the error precisely. NVML failed with `N/A` rather than `Not Supported`, which meant "
         "the binary was present but could not reach the driver - so injection was partially working. That "
         "sent me back through the generation log, where one warning line said the library could not be "
         "located. `nvidia-ctk` looks in the WSL driver store; Docker Desktop puts it elsewhere."),
        ("Why is the repo inside WSL rather than on the Windows drive?",
         "Performance and correctness. The Windows mount is slow for many small files and does not honour "
         "Unix permission bits, which matters for the age keys and signing material from M2 onward."),
        ("Why pin tool versions?",
         "Reproducibility. `latest` is not a version you can return to. My installer compares the installed "
         "version against the pin and reinstalls only on mismatch, so it is both idempotent and an upgrade "
         "path. I verify each pin exists upstream before committing it - I initially pinned a Trivy version "
         "that had never been released."),
    ]
    for q, a in qs:
        par = D.d.add_paragraph()
        par.paragraph_format.space_before = Pt(9)
        par.paragraph_format.space_after = Pt(2)
        par.paragraph_format.keep_with_next = True
        r = par.add_run(q)
        r.bold = True; r.font.size = Pt(10.5); r.font.name = BODY_FONT; r.font.color.rgb = TEAL_D
        b = D.d.add_paragraph()
        b.paragraph_format.left_indent = Inches(0.22)
        b.paragraph_format.space_after = Pt(3)
        add_rich(b, a, size=10.2)


def glossary_and_next(D):
    D.h1("10. New Terms From M0")
    D.table(
        ["Term", "Plain meaning"],
        [
            ["**WSL2**", "Windows Subsystem for Linux - a real Linux kernel running in a lightweight VM on Windows, sharing the machine's hardware."],
            ["**k3d / k3s**", "k3s is a small but complete Kubernetes. k3d runs it inside Docker containers, so a cluster is one command to create and one to destroy."],
            ["**containerd**", "The component inside a Kubernetes node that actually starts and stops containers."],
            ["**RuntimeClass**", "A named way of starting containers. `nvidia` routes them through the NVIDIA runtime instead of plain runc, which is what allows GPU access."],
            ["**CDI**", "Container Device Interface - a written specification of which device files and libraries to inject into a container."],
            ["**NVML**", "NVIDIA Management Library - the standard way to query a GPU. Unsupported under WSL2."],
            ["**/dev/dxg**", "The paravirtualised GPU device WSL2 exposes instead of the usual `/dev/nvidia*`. The real driver stays on the Windows side."],
            ["**DaemonSet**", "A Kubernetes object that runs exactly one copy of a pod on every matching node."],
            ["**Node affinity**", "Rules restricting which nodes a pod may run on. If no node matches, nothing runs - and no error is raised."],
            ["**Init container**", "A container that must finish successfully before the main one starts. Used from M3 to verify model weights."],
            ["**Idempotent**", "Safe to run repeatedly with the same result. The toolchain installer is idempotent."],
            ["**ADR**", "Architecture Decision Record - a one-page note of a decision, the alternatives, and the consequences."],
        ],
        widths=[1.35, 5.25],
        size=9.3,
    )

    D.h1("11. Open Items Going Into M1")
    D.table(
        ["Item", "Status", "Action"],
        [
            ["Docker data disk on D: (12.5 GB free)", "**Blocking M1**",
             "vLLM's image is ~10 GB. Move to `E:\\WSL\\Docker` via Docker Desktop > Settings > Resources > "
             "Advanced > Disk image location. Must be done in the GUI."],
            ["C: drive headroom", "Improved, still tight",
             "4.7 GB free after reclaiming 3.4 GB of caches. Worth a deeper clean-up when convenient."],
            ["Git remote", "Not configured",
             "Repo is local only. A public GitHub repo is needed before M2's CI pipeline."],
            ["No scheduler GPU accounting", "Accepted",
             "Documented in ADR 0002. Revisit only if the project moves to native Linux."],
        ],
        widths=[1.7, 1.1, 3.8],
    )
    D.spacer(4)
    D.callout("Where M1 goes",
              "**M1 - The inference service (Days 2-4).** vLLM serving Qwen2.5-0.5B on the GPU, and the "
              "first version of `palisade-gateway` in FastAPI with an OpenAI-compatible "
              "`/v1/chat/completions` endpoint. Done when you `curl` the gateway and watch tokens stream "
              "back from your own hardware.", "note")
