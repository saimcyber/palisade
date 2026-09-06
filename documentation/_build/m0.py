# -*- coding: utf-8 -*-
"""Content for the M0 engineering document."""
from docx_kit import *   # noqa: F403


# --- the device used throughout: the same idea said twice ---------------------
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


def _steps(D, items, prefix="Step"):
    for i, (title, body) in enumerate(items, 1):
        par = D.d.add_paragraph()
        par.paragraph_format.left_indent = Inches(0.30)
        par.paragraph_format.space_before = Pt(5)
        par.paragraph_format.space_after = Pt(1)
        par.paragraph_format.keep_with_next = True
        r = par.add_run(f"{prefix} {i}.  {title}")
        r.bold = True; r.font.size = Pt(10.5); r.font.name = BODY_FONT; r.font.color.rgb = TEAL_D
        b = D.d.add_paragraph()
        b.paragraph_format.left_indent = Inches(0.30)
        b.paragraph_format.space_after = Pt(4)
        add_rich(b, body, size=10.2)


def _qa(D, pairs):
    for q, a in pairs:
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
    r = p2.add_run("Engineering Log  \u00b7  Milestone M0")
    r.font.size = Pt(17); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xC9, 0xE6, 0xE9)
    p3 = c.add_paragraph(); no_space(p3, 4, 18)
    r = p3.add_run("Foundations: a GPU-capable Kubernetes cluster on a laptop")
    r.italic = True; r.font.size = Pt(11); r.font.name = BODY_FONT
    r.font.color.rgb = RGBColor(0xA8, 0xD2, 0xD7)

    D.spacer(8)
    D.table(
        ["Field", "Detail"],
        [
            ["Milestone", "**M0 - Foundations** (Day 1 of 20)"],
            ["Completed", "6-7 September 2026"],
            ["Goal", "`make up` produces a local Kubernetes cluster in which a scheduled pod can use the GPU"],
            ["Result", "**Passed.** 28/28 environment checks, verified from a clean teardown and rebuild"],
            ["Hardware", "NVIDIA RTX 3050 Laptop (4 GB VRAM), 16 GB RAM, 12 logical CPUs, Windows 11 + WSL2"],
            ["Repository", "`~/palisade` inside WSL2 Ubuntu 24.04 (distro installed on the E: drive)"],
            ["Commits", "5 commits, 37 tracked files"],
        ],
        widths=[1.35, 5.25],
    )

    D.h2("How this document is organised")
    D.p("It was written to answer six specific questions. This table says where each is answered, so nothing "
        "has to be hunted for.", color=SLATE, after=8)
    D.table(
        ["The question", "Where it is answered"],
        [
            ["**1. Everything that was done**",
             "§4 What was built (the inventory) and **§5 How it was done** (the complete command-level walkthrough)"],
            ["**2. What was done differently**, and why",
             "**§8 Deviations from the plan** - eight of them, each with the reason"],
            ["**3. How it was done**",
             "**§5** step by step with real commands, plus the two deep dives in §6 and §7"],
            ["**4. What the limitations are**",
             "**§10 Limitations** - seven, each with an honest position rather than an excuse"],
            ["**5. Why this tool/approach over the alternatives**",
             "**§9 Tool choices** - what was rejected and why; also §3 for the up-front decisions"],
            ["**6. Plain language and technical, both**",
             "Throughout. Every significant idea appears as an **IN PLAIN LANGUAGE** / **TECHNICALLY** pair."],
        ],
        widths=[2.1, 4.5],
    )

    D.callout("The one thing to take away from M0",
              "Two pieces of infrastructure - the GPU and Docker's storage - each refused to work on the "
              "first attempt, and each failed **silently**: a tool reported success while having done "
              "nothing useful. Sections 6 and 7 are the investigations. They are worth more than the rest "
              "of the milestone combined, because a milestone that goes smoothly teaches nothing.", "ok")


# =============================================================================
def what_it_was_for(D):
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
              "**Sequence work by risk, not by convenience.** The most uncertain dependency goes first, with "
              "a time limit and a pre-agreed fallback. Doing the easy parts first feels productive and hides "
              "the thing that can kill the project until you have spent two weeks on it.", "note")

    D.h2("1.3  The tasks, and how they turned out")
    D.table(
        ["#", "Task", "Outcome"],
        [
            ["0.1", "Verify the GPU end to end", "**Done** - after three separate failures (\u00a76)"],
            ["0.2", "Install the toolchain, add `make doctor`", "**Done** - 15 pinned tools, 28 checks"],
            ["0.3", "Repo skeleton, Makefile, licence, pre-commit", "**Done** - 37 files, 5 commits"],
            ["0.4", "Cluster profiles (`up-lite` / `up-full`)", "**Done** - RAM-constrained by design"],
            ["0.5", "Cap WSL2 memory", "**Done** - 10 GB cap, 8 CPUs, swap on E:"],
            ["+", "**Install a Linux distribution**", "**Added** - none existed (\u00a72)"],
            ["+", "**Relocate Docker's storage**", "**Added** - the original drive was too small (\u00a77)"],
            ["+", "**Set up project documentation**", "**Added** - `documentation/`, one document per milestone"],
        ],
        widths=[0.4, 2.9, 3.3],
    )


# =============================================================================
def starting_point(D):
    D.h1("2. What the Machine Looked Like Before")
    D.p("The plan assumed a working WSL2 + Docker setup with an untested GPU. Reality differed in several "
        "ways that mattered, and finding them **before** installing anything saved a great deal of rework.")

    D.table(
        ["What was checked", "What was found", "Why it mattered"],
        [
            ["GPU", "RTX 3050 Laptop, **4 GB VRAM**, driver 616.64",
             "4 GB confirms the model choice: Qwen2.5-0.5B, not something larger. Sizing the model to the "
             "hardware is a decision, not a compromise."],
            ["WSL distributions", "**None.** Only Docker Desktop's internal `docker-desktop` distro",
             "There was no Linux to work in at all. A full Ubuntu install had to be added to the milestone."],
            ["Docker Desktop", "Installed (4.86.0) and previously used",
             "It held a **19.9 GB data disk on D:** containing real work, including a live Supabase stack "
             "with database volumes."],
            ["C: drive", "**4.6 GB free**, later dropping to 1.4 GB",
             "Dangerously low. Windows itself needs headroom, and nothing new could be installed there."],
            ["D: drive", "12.5 GB free, holding Docker's data",
             "**Too small for vLLM's ~10 GB image**, which lands in M1. This became \u00a77."],
            ["E: drive", "102 GB free",
             "The only viable home for WSL, Docker data and model weights."],
            ["RAM", "15.2 GB total, 12 logical CPUs",
             "Forced the `up-lite` / `up-full` profile split - the full stack will not fit alongside a GPU "
             "workload."],
        ],
        widths=[1.15, 2.15, 3.3],
    )

    D.callout("A judgement call worth recording",
              "Docker's existing data disk contained **11 running containers belonging to an unrelated, "
              "active project** (a Supabase stack). The tempting move - wipe Docker and start clean - would "
              "have destroyed someone's working database. Nothing was deleted without asking, and even then "
              "only genuinely dead artefacts (5-month-old minikube images, build cache) were removed. "
              "**Read the inventory before you clean.**", "warn")


# =============================================================================
def decisions(D):
    D.h1("3. Decisions Taken Before Writing Any Code")
    D.p("Four decisions were made up front because each would have been expensive to reverse later. Each is "
        "recorded with the alternatives that were rejected.")

    D.h2("3.1  Develop inside WSL2 Ubuntu, not on Windows")
    dual(D,
         "Work inside a real Linux system running on the Windows machine, rather than using Windows tools "
         "directly. Almost every tool in this project was built for Linux first, and the servers this "
         "project imitates all run Linux.",
         "Install Ubuntu 24.04 as a WSL2 distribution and treat it as the development host. Docker Desktop "
         "exposes its daemon into the distro through WSL integration, so containers, k3d and the GPU are all "
         "reachable natively.")
    D.table(
        ["Option", "Verdict"],
        [
            ["**WSL2 Ubuntu** (chosen)",
             "Native Linux tooling, correct file permissions, matches what a real deployment looks like, and "
             "GPU passthrough is supported."],
            ["Windows tooling directly",
             "Rejected. Most tools have Windows builds, but shell scripting, Makefiles and file permissions "
             "become a constant source of friction - and the portfolio value of 'I did this on Linux' is lost."],
            ["A conventional VM (VirtualBox / Hyper-V)",
             "Rejected. Heavier on a 16 GB machine, and GPU passthrough into a conventional VM is far harder "
             "than WSL2's built-in support."],
            ["Dual-boot Linux",
             "Rejected as too disruptive, though it is genuinely the simplest technical path and remains a "
             "reasonable future move."],
        ],
        widths=[1.75, 4.85],
    )

    D.h2("3.2  Put everything on the E: drive")
    dual(D,
         "The main Windows drive was nearly full, so Linux and all its large files were installed on the "
         "spare drive with 100 GB free.",
         "Ubuntu installed with `wsl --install --location E:\\WSL\\Ubuntu`, WSL swap at `E:\\WSL\\swap.vhdx` "
         "via `.wslconfig`, and Docker's data disk later relocated to `E:\\WSL\\Docker` (\u00a77).")

    D.h2("3.3  Keep the repository inside the Linux filesystem")
    dual(D,
         "The project's code lives inside Linux's own storage rather than on the Windows drive, because "
         "reaching across from Linux to Windows files is slow and loses information about file permissions.",
         "The repo is at `~/palisade` on ext4 inside the WSL2 VM, not on `/mnt/e`. The Windows drive is "
         "mounted through 9p/DrvFs, which is markedly slower for many small files and does not honour Unix "
         "permission bits - which matters for the `age` private keys, cosign material and executable script "
         "bits used from M2 onward.")
    D.p("Accessible from Windows at `\\\\wsl$\\Ubuntu-24.04\\home\\saim\\palisade`, and pushed to GitHub "
        "regardless, so nothing is trapped.")

    D.h2("3.4  Pin every tool version, and verify the pins exist")
    dual(D,
         "Every tool is installed at an exact version written down in a script, not 'whatever is newest "
         "today'. Otherwise the setup quietly changes underneath you and breaks for reasons you cannot trace.",
         "`scripts/install-tools.sh` declares an explicit version constant per tool and compares it against "
         "the installed binary, reinstalling only on mismatch. This makes the script idempotent **and** an "
         "upgrade mechanism.")
    D.callout("A mistake made and corrected here",
              "The first version of the installer used pins that were **all significantly out of date** - "
              "Helm 3.16 when 4.2.4 is current, k6 0.55 against 2.2.0 - and a Trivy version that had never "
              "existed, which failed with a 404. The fix was to query each project's release API and confirm "
              "every download URL returned HTTP 200 *before* rewriting the script. **Never pin a version you "
              "have not confirmed exists.**", "danger")


# =============================================================================
def what_was_built(D):
    D.h1("4. What Was Built")

    D.h2("4.1  The environment")
    D.table(
        ["Layer", "What was done", "Detail"],
        [
            ["WSL2 config", "Wrote `%USERPROFILE%\\.wslconfig`",
             "10 GB RAM cap, 8 of 12 CPUs, 4 GB swap on E:, `autoMemoryReclaim=gradual`"],
            ["Distribution", "Installed Ubuntu 24.04.4 LTS to E:",
             "`wsl --install Ubuntu-24.04 --location E:\\WSL\\Ubuntu --no-launch`"],
            ["User", "Created `saim` non-interactively",
             "`sudo` + `adm` groups, **locked password** with passwordless sudo, systemd enabled via `/etc/wsl.conf`"],
            ["Docker", "Enabled WSL integration",
             "Injected `/usr/bin/docker`; required a distro restart to wire the socket"],
            ["Docker storage", "Relocated D: -> E: (\u00a77)",
             "19.9 GB data disk moved; D: freed from 12.5 GB to 32.6 GB"],
        ],
        widths=[1.05, 1.85, 3.7],
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
+-- docs/CONVENTIONS.md                conventions, GPU gotchas, the documentation rule
+-- scripts/
|   +-- install-tools.sh     pinned, version-aware, idempotent toolchain installer
|   +-- doctor.sh            28 environment checks; exits non-zero so CI can gate on it
|   +-- build-k3s-image.sh   builds the GPU-capable node image
|   +-- cluster-up.sh        creates the cluster; branches WSL2 vs native Linux
|   +-- setup-gpu-cdi.sh     the GPU fix (section 6)
|   +-- cluster-down.sh      teardown, with --purge
+-- docker/k3s-nvidia/       Dockerfile for the custom k3s node image
+-- k8s/gpu-check.yaml       the M0 acceptance test, as a Job
+-- docs/adr/                0001 record decisions - 0002 the GPU investigation
+-- documentation/           this document, and its generator
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
            ["pre-commit, ruff", "current", "Lint and format on every commit."],
        ],
        widths=[1.15, 1.1, 4.35],
    )


# =============================================================================
def how_it_was_done(D):
    D.h1("5. How It Was Done - the Complete Walkthrough")
    D.p("The full sequence, in order, with the commands that mattered. This is the section to follow if you "
        "want to reproduce the environment from nothing.", color=SLATE)

    D.h2("5.1  Survey before touching anything")
    D.p("No installation happened until the machine had been inventoried. Three of the findings changed the "
        "plan, which is the entire argument for surveying first.")
    D.code("""wsl --status ; wsl --list --verbose      # -> no Linux distro at all
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
Get-PSDrive -PSProvider FileSystem       # -> C: 4.6GB, D: 12.5GB, E: 102GB
docker images ; docker ps -a             # -> an active Supabase stack. Do not wipe.""")

    D.h2("5.2  Cap the WSL2 virtual machine")
    dual(D,
         "Tell the Linux environment how much of the laptop it is allowed to use, so Windows stays usable.",
         "`%USERPROFILE%\\.wslconfig`. The cap applies to the **whole WSL2 utility VM** - Ubuntu, the "
         "`docker-desktop` distro and every k3d container share it. That is precisely why the stack later "
         "had to be split into `up-lite` and `up-full`.")
    D.code("""[wsl2]
memory=10GB          # of 15.2 GB; Windows keeps the rest
processors=8         # of 12
swap=4GB
swapFile=E:\\\\WSL\\\\swap.vhdx
localhostForwarding=true

[experimental]
autoMemoryReclaim=gradual""")

    D.h2("5.3  Install Ubuntu onto E:, without an interactive prompt")
    D.p("`wsl --install` normally stops to ask for a username and password. `--no-launch` registers the "
        "distribution without that prompt, so the account can be created deterministically afterwards.")
    D.code("""wsl --install Ubuntu-24.04 --location E:\\\\WSL\\\\Ubuntu --no-launch

# then, as root inside the distro:
useradd -m -s /bin/bash -G sudo,adm saim
passwd -l saim                                   # lock it: no weak password to leak
echo "saim ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-saim
cat > /etc/wsl.conf <<EOF
[user]
default=saim
[boot]
systemd=true
EOF""")

    D.h2("5.4  Install the toolchain")
    D.p("`scripts/install-tools.sh` is version-aware rather than merely idempotent: it extracts the "
        "installed version, compares it with the pin, and reinstalls only on a mismatch. The same script is "
        "therefore both the installer and the upgrade path.")
    D.code("""needs() {                       # returns 0 when an install is required
  local bin="$1" want="${2#v}"; shift 2
  [ "$FORCE" = "1" ] && return 0
  command -v "$bin" >/dev/null 2>&1 || return 0
  local cur; cur="$( "$@" 2>/dev/null | head -1 | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' | head -1 )"
  [ "$cur" = "$want" ] && return 1
  WAS="$cur"; return 0
}""")
    D.callout("The Windows-shadowing trap",
              "`aws` initially resolved to a **Windows** Python shim at `/mnt/c/...` that cannot execute "
              "under Linux. WSL appends the Windows PATH by default, so Windows executables appear inside "
              "Linux and silently win wherever no Linux equivalent exists. The installer now tests for a "
              "real binary at `/usr/local/bin/aws` rather than trusting `command -v`, and `make doctor` "
              "prints the resolved path of every tool and flags anything under `/mnt/`.", "warn")

    D.h2("5.5  Build a k3s node image that can pass on the GPU")
    dual(D,
         "The standard Kubernetes-in-Docker image has no NVIDIA software inside it. Even when the outer "
         "container can see the graphics card, it has no way to hand it to the programs it runs. So a "
         "custom image is built with the NVIDIA pieces included.",
         "The k3s rootfs is overlaid onto an `nvidia/cuda` base carrying `nvidia-container-toolkit`. On "
         "startup k3s scans for known container runtimes, finds `nvidia-container-runtime`, writes a "
         "containerd configuration exposing it, and creates the `nvidia` RuntimeClass automatically.")
    D.code("""# syntax=docker/dockerfile:1.7-labs
ARG K3S_TAG=v1.36.4-k3s1
ARG CUDA_TAG=12.8.1-base-ubuntu24.04

FROM rancher/k3s:${K3S_TAG} AS k3s
FROM nvidia/cuda:${CUDA_TAG}

RUN apt-get update && apt-get install -y --no-install-recommends nvidia-container-toolkit

COPY --from=k3s / / --exclude=/bin      # /bin copied separately: k3s would
COPY --from=k3s /bin /bin               # otherwise clobber the CUDA image's own""")

    D.h2("5.6  Create the cluster")
    D.code("""k3d cluster create palisade \\\\
  --image palisade/k3s-nvidia:v1.36.4-k3s1 \\\\
  --gpus all \\\\
  --api-port 6550 \\\\
  --port 8080:80@loadbalancer --port 8443:443@loadbalancer \\\\
  --agents 0 \\\\
  --k3s-arg "--disable=metrics-server@server:0" \\\\
  --wait""")
    D.p("`--agents 0` keeps it to a single node: on one GPU a second node adds memory cost and no capability. "
        "`metrics-server` is disabled for the same reason - it is not needed until M4.")

    D.h2("5.7  Wire the GPU in (the part that took three attempts)")
    D.p("Covered in full in \u00a76. The resulting automation is `scripts/setup-gpu-cdi.sh`:")
    D.code("""nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml   # inside the node container
# then append the mount that nvidia-ctk omits on WSL:
#   /usr/lib/x86_64-linux-gnu/libdxcore.so
# then pin the runtime:
sed -i 's/^mode = "auto"/mode = "cdi"/' /etc/nvidia-container-runtime/config.toml""")

    D.h2("5.8  Prove it, from nothing")
    D.p("The acceptance test is a **Job**, not a `docker run`. That distinction is the point: it proves the "
        "whole chain including the Kubernetes scheduler, not just Docker.")
    D.code("""make down          # full teardown - do not test against a cluster that already works
make up            # rebuild from scratch
make gpu-check     # -> M0 ACCEPTANCE PASSED
make doctor        # -> 28 passed, 0 warnings, 0 failed""")
    D.callout("Why teardown-and-rebuild matters",
              "Testing against the cluster you have been poking at all day proves only that the machine is "
              "in a good state - not that your automation can produce that state. Rebuilding from scratch is "
              "what exposed the `nvidia` RuntimeClass race in \u00a710, which had been invisible until then.",
              "note")


# =============================================================================
def gpu_problem(D):
    D.h1("6. Deep Dive A - The GPU Problem, Three Failures")
    D.p("The GPU worked at every layer until the very last one, then failed three times for three unrelated "
        "reasons. Each is worth understanding on its own.", color=SLATE)

    D.h2("6.1  What already worked")
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
        "reaching the node container but was not being handed on to containers *inside* it.")

    D.h2("6.2  Failure 1 - Helm reported success and deployed nothing")
    dual(D,
         "The standard tool for sharing a GPU with Kubernetes was installed and the installer reported "
         "success. But it had not started anything: it had been told to run only on machines carrying a "
         "particular label, and no machine had that label. So it ran on zero machines and reported no error.",
         "The `nvidia-device-plugin` chart carries a default `nodeAffinity` requiring one of "
         "`feature.node.kubernetes.io/pci-10de.present`, "
         "`feature.node.kubernetes.io/cpu-model.vendor_id=NVIDIA`, or `nvidia.com/gpu.present`. Those labels "
         "are applied by NVIDIA's Node Feature Discovery, which had been disabled (`gfd.enabled=false`) to "
         "save memory. The DaemonSet was created correctly and matched no nodes: `DESIRED = 0`.")
    D.callout("Lesson 1",
              "**A successful `helm install` means the objects were created, not that anything is running.** "
              "`--wait` waits for what exists; if a DaemonSet wants zero pods, zero pods is a satisfied "
              "state. Check `DESIRED`, never the exit code alone.", "danger")
    D.p("**Fix:** label the node explicitly - `kubectl label node --all nvidia.com/gpu.present=true`. This "
        "now happens automatically in `cluster-up.sh` on the native-Linux path, with a comment explaining why.")

    D.h2("6.3  Failure 2 - NVML is not supported under WSL2")
    D.p("With scheduling fixed, the plugin started and immediately crash-looped:")
    D.code("""E  Failed to initialize NVML: Not Supported
E  If this is a GPU node, did you set the docker default runtime to `nvidia`?
E  error starting plugins: ... nvml init failed: Not Supported""", size=8.5)
    dual(D,
         "The tool asks the graphics driver to introduce itself using a standard interface. On Windows "
         "running Linux inside it, the graphics card is not presented in the normal way - it is a special "
         "shared device - and that standard interface simply does not exist. No setting fixes this.",
         "The device plugin enumerates GPUs through **NVML**. Under WSL2 the GPU is exposed as `/dev/dxg`, a "
         "paravirtualised interface, with the real driver on the Windows side. NVML has no support for that "
         "model. The device plugin **cannot work under WSL2** - this is architectural, not configuration.")
    D.callout("Lesson 2",
              "**Know the difference between 'misconfigured' and 'impossible'.** Time spent tuning a "
              "component that cannot work in your environment is time wasted. Recognising the second "
              "category quickly is what kept this inside its half-day budget.", "danger")

    D.h2("6.4  The alternative - CDI")
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

    D.h2("6.5  Failure 3 - one warning line was the whole problem")
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
         "missing mount resolved it immediately.")
    D.callout("Lesson 3",
              "**Warnings are not decoration.** A tool that warns and continues will hand you a "
              "plausible-looking artefact with a hole in it. This one line was the difference between a "
              "working cluster and a day of confusion.", "danger")

    D.h2("6.6  The result")
    D.code("""+-----------------------------------------------------------------------------+
| NVIDIA-SMI 615.65.07       KMD Version: 616.64     CUDA UMD Version: 13.4   |
|   0  NVIDIA GeForce RTX 3050 ...  On  |  0MiB / 4096MiB  |  0%   Default    |
+-----------------------------------------------------------------------------+
GPU 0: NVIDIA GeForce RTX 3050 Laptop GPU (UUID: GPU-6d9e8048-...)

PASS: the scheduler placed this pod and it can drive the GPU.
M0 ACCEPTANCE PASSED""", size=8.0)
    D.p("Pods now need exactly two things, and `k8s/gpu-check.yaml` documents both:")
    D.code("""runtimeClassName: nvidia
metadata:
  annotations:
    cdi.k8s.io/gpu: "nvidia.com/gpu=all\"""", size=8.5)


# =============================================================================
def docker_move(D):
    D.h1("7. Deep Dive B - Relocating Docker's Storage")
    D.p("A second piece of infrastructure that failed silently, and the second time in one milestone that a "
        "tool reported success while having achieved nothing.", color=SLATE)

    D.h2("7.1  Why it had to move")
    dual(D,
         "Docker keeps all its downloaded software in one big file. That file was on a drive with only "
         "12.5 GB of room left, and the next milestone needs to download a single item of about 10 GB. It "
         "would not fit.",
         "Docker Desktop's `docker_data.vhdx` (19.9 GB) sat under `D:\\AWS\\Docker\\...` with 12.5 GB free "
         "on D:. The `vllm/vllm-openai` image is roughly 10 GB. E: had ~100 GB free.")

    D.h2("7.2  The GUI move half-completed - and said nothing")
    D.p("The vendor-supported path is Docker Desktop's own setting (Settings > Resources > Advanced > Disk "
        "image location), which triggers an internal migration. It ran, and it did not finish. The state "
        "afterwards was genuinely misleading:")
    D.table(
        ["Signal", "What it showed", "What it meant"],
        [
            ["`E:` copy exists, 19.93 GB", "modified 21:55, **not** file-locked", "A stale, orphaned copy"],
            ["`D:` copy exists, 19.93 GB", "modified 22:04, **file-locked**", "**This is the live one**"],
            ["`CustomWslDistroDir`", "still `D:\\AWS\\Docker\\...`", "Docker never switched over"],
            ["WSL registry `BasePath`", "`\\\\?\\D:\\AWS\\Docker\\...\\main`", "The distro was still on D:"],
        ],
        widths=[1.5, 2.2, 2.9],
    )
    D.callout("How to tell which file a service is really using",
              "Not by its name or its date - by **whether the operating system has it open**. Attempting an "
              "exclusive `File.Open` and catching the failure is a definitive test, and it is what settled "
              "this in seconds. The second confirmation was the WSL registry's `BasePath`, which is the "
              "authority on where a distribution actually lives.", "note")

    D.h2("7.3  Doing it manually")
    D.p("Ordered so that the original stayed intact and untouched until the new location was proven:")
    _steps(D, [
        ("Stop everything cleanly",
         "`docker desktop stop`, then `wsl --shutdown`, then confirm no `*docker*` processes remain. A "
         "20 GB file cannot be moved while it is open."),
        ("Delete the stale copy",
         "Removing the orphaned E: copy first, both to reclaim 19.9 GB and to give the real copy a clean "
         "destination."),
        ("Move the distribution with WSL's own tool",
         "`wsl --manage docker-desktop --move E:\\WSL\\Docker\\DockerDesktopWSL\\main`. This is preferable to "
         "moving files by hand because **WSL updates its own registry entry**; a manual move would leave the "
         "registry pointing at a path that no longer exists."),
        ("Copy - do not move - the data disk",
         "`robocopy ... /J` (unbuffered I/O, appropriate for very large files). 19.934 GB in 4.8 minutes at "
         "~74 MB/s. Copying rather than moving leaves the original as a fallback."),
        ("Repoint the setting",
         "`CustomWslDistroDir` -> `E:\\WSL\\Docker\\DockerDesktopWSL` in "
         "`%APPDATA%\\Docker\\settings-store.json`, with a backup taken first."),
        ("Start, then verify before deleting anything",
         "Confirm the **E:** file is now the locked one, then check the inventory: 29 images, all volumes "
         "present, and the unrelated Supabase stack back up and healthy."),
        ("Only then remove the original",
         "D: went from 12.5 GB to **32.6 GB** free."),
    ])

    D.h2("7.4  The sting in the tail - the Docker socket vanished")
    dual(D,
         "After all the restarting, Linux could no longer talk to Docker at all. The connection point simply "
         "was not there. Restarting Docker did not bring it back.",
         "`/var/run/docker.sock` was not re-provisioned into the Ubuntu distro after `wsl --shutdown`. "
         "Everything else was in place - the CLI was symlinked to `/mnt/wsl/docker-desktop/cli-tools`, and "
         "all the proxy sockets existed under `shared-sockets/guest-services/` - but the symlink itself was "
         "never created. Neither a Docker restart nor a distro restart fixed it.")
    D.p("What worked was forcing Docker Desktop to re-run its integration provisioning by toggling the "
        "distribution out of the list and back in:")
    D.code("""docker desktop stop
#   settings-store.json:  "IntegratedWslDistros": []
docker desktop start ; docker desktop stop
#   settings-store.json:  "IntegratedWslDistros": ["Ubuntu-24.04"]
docker desktop start
# -> srw-rw---- 1 root docker 0 /var/run/docker.sock""")
    D.callout("Worth remembering",
              "**Some state is only created on a transition, not on startup.** Docker Desktop provisions the "
              "socket when a distribution *becomes* integrated, not every time it starts. When something is "
              "missing that should exist, forcing the transition is often the fix - and it is far cheaper "
              "than reinstalling. This is now recorded in `docs/CONVENTIONS.md`.", "note")

    D.h2("7.5  Outcome")
    D.table(
        ["Drive", "Before", "After"],
        [
            ["C:", "1.4 GB free", "**4.6 GB** (caches cleared)"],
            ["D:", "12.5 GB free, holding Docker", "**32.6 GB**, Docker data gone"],
            ["E:", "102 GB free", "**77.5 GB**, holding Ubuntu + Docker + swap"],
        ],
        widths=[0.8, 2.6, 3.2],
    )
    D.p("`make gpu-check` passes after the move, so M1 is unblocked with roughly 77 GB of headroom for "
        "vLLM, model weights and the images still to come.")


# =============================================================================
def deviations(D):
    D.h1("8. What Was Done Differently, and Why")
    D.p("Eight departures from the written plan. Each was a response to something the plan could not have "
        "known, and each is recorded rather than quietly absorbed.")

    D.table(
        ["#", "The plan said", "What was done instead", "Why"],
        [
            ["1", "WSL2 and Docker are working; GPU untested",
             "Installed Ubuntu 24.04 from scratch",
             "There was **no Linux distribution at all** - only Docker's internal one. The plan's premise "
             "was simply wrong."],
            ["2", "Use the NVIDIA device plugin so pods request `nvidia.com/gpu`",
             "Use **CDI injection** on WSL2; keep the device plugin for native Linux",
             "The device plugin cannot function under WSL2 (\u00a76.3). Branching on host keeps the repo "
             "portable and makes the difference explicit rather than accidental."],
            ["3", "Install the listed toolchain",
             "Verified every version against upstream release APIs first",
             "The original pins were badly out of date and one had never existed. Verification is now part "
             "of the process, not an afterthought."],
            ["4", "k3s v1.31.5, CUDA 12.4, Helm 3",
             "k3s v1.36.4, CUDA 12.8, Helm 4.2.4",
             "Current versions. A portfolio project running two-year-old components invites an awkward "
             "question in an interview."],
            ["5", "Nothing about existing machine state",
             "Audited Docker's contents; deleted only what was approved",
             "The machine held an active Supabase project with live database volumes. Destroying it would "
             "have been unacceptable."],
            ["6", "Nothing about drive layout",
             "Moved Docker's 19.9 GB data disk D: -> E: (\u00a77)",
             "D: had 12.5 GB free and M1 needs a ~10 GB image. This would have blocked the next milestone "
             "outright."],
            ["7", "Nothing about C: drive",
             "Reclaimed ~7 GB of caches across two passes",
             "C: had fallen to **1.4 GB free**, which risks Windows stability and breaks tooling that needs "
             "temporary space."],
            ["8", "A `learning/` folder of private notes",
             "A public `documentation/` folder, generated from source",
             "The write-ups are being published as project documentation, so the framing changed with the "
             "name. Generating from source keeps every milestone document structurally identical."],
        ],
        widths=[0.3, 1.5, 1.75, 3.05],
    )

    D.callout("A deviation worth more than the original plan",
              "Deviation 2 turned a routine 'install the standard plugin' step into a genuine investigation "
              "with a written ADR. **When an interviewer asks about a hard problem you solved, this is the "
              "answer** - and it only exists because the environment refused to cooperate. Do not smooth "
              "these out of the record.", "ok")


# =============================================================================
def tool_choices(D):
    D.h1("9. Tool Choices - What Was Picked and What Was Rejected")
    D.p("In an interview the reasoning matters more than the selection. Each row is a decision you should be "
        "able to defend in two sentences.")

    D.table(
        ["Decision", "Chosen", "Rejected, and why"],
        [
            ["Local Kubernetes", "**k3d** (k3s in Docker)",
             "**minikube** - heavier, and its GPU story on WSL2 is no better. **kind** - viable, but k3d "
             "gives a real k3s distribution, matching what small companies actually run. **Docker Desktop's "
             "built-in Kubernetes** - no control over the node image, which this project specifically needs."],
            ["GPU into pods", "**CDI**",
             "**NVIDIA device plugin** - architecturally impossible on WSL2. **Privileged pods with manual "
             "device mounts** - would work, but is a security anti-pattern in a project whose entire theme "
             "is security."],
            ["Node image", "**Custom k3s + nvidia-container-toolkit**",
             "**Stock `rancher/k3s`** - contains no NVIDIA runtime, so containerd inside the node cannot "
             "pass the GPU on, even though the node itself can see it."],
            ["Moving Docker's data", "**`wsl --manage --move` + robocopy**",
             "**The Docker Desktop GUI** - tried first as the vendor-supported path; it half-completed "
             "silently. **Moving the folder by hand** - would leave the WSL registry pointing at a "
             "non-existent path."],
            ["Copy vs move (20 GB)", "**Copy, verify, then delete**",
             "**`robocopy /MOVE`** - faster and simpler, but leaves no fallback if the new location fails to "
             "start. The extra 5 minutes bought a guaranteed rollback."],
            ["Secrets (from M3)", "**SOPS + age**",
             "**HashiCorp Vault** - roughly 1 GB of RAM for capability SOPS already provides, and it sits "
             "outside the GitOps model rather than inside it. **Sealed Secrets** - viable, but SOPS keeps "
             "files readable and reviewable in Git."],
            ["Task runner", "**Make**",
             "**Shell scripts alone** - no discoverability. **Taskfile / just** - nicer, but Make is present "
             "everywhere and is what a reviewer expects to find."],
            ["Version strategy", "**Exact pins, verified upstream**",
             "**`latest` tags** - not reproducible; the setup changes underneath you. **Distribution "
             "packages** - usually years out of date."],
            ["Documentation format", "**Generated .docx + Markdown ADRs**",
             "**Hand-written documents** - drift apart in structure and cannot be corrected at the source. "
             "**A wiki** - decisions must live beside the code they explain and be reviewable in the same "
             "pull request."],
        ],
        widths=[1.05, 1.5, 4.05],
    )


# =============================================================================
def limitations(D):
    D.h1("10. Limitations of This Setup")
    D.p("Being able to state what a system *cannot* do is a stronger signal than claiming it does "
        "everything. These are real, and should be said out loud rather than discovered by a reviewer.")

    D.table(
        ["Limitation", "What it means in practice", "Honest position"],
        [
            ["**No scheduler-level GPU accounting**",
             "Nothing requests `nvidia.com/gpu`, so Kubernetes does not know the GPU exists and would "
             "happily place two GPU pods on the same node.",
             "With one GPU and one vLLM replica it does not bite. It also reinforces a decision taken "
             "independently: Palisade does not autoscale the model tier, it does admission control and load "
             "shedding at the gateway."],
            ["**4 GB of VRAM**",
             "Only small models fit. Qwen2.5-0.5B in fp16 is roughly 1 GB of weights plus KV cache.",
             "Deliberate, and irrelevant to the DevOps story - the model is one Helm value. Everything of "
             "value sits in front of it and is model-agnostic."],
            ["**10 GB for the whole Linux side**",
             "Argo CD, Prometheus, Grafana and a GPU workload cannot all run at once.",
             "The `up-lite` / `up-full` split. Turning off what you are not working on is a real operational "
             "decision on constrained hardware, not a shortcut."],
            ["**Single node**",
             "No multi-node scheduling, no node-failure testing, no topology spread.",
             "Out of scope. Chaos testing in M5 targets pod and dependency failure instead."],
            ["**CDI spec is generated at runtime**",
             "It cannot be baked into the node image, because the WSL driver store path is host-specific.",
             "`cluster-up.sh` regenerates it on every cluster creation, so it is reproducible even though it "
             "is not static. After a Docker restart, `make gpu-cdi` re-applies it."],
            ["**Two steps are not fully automated**",
             "Docker's disk location needs the GUI (and even then may not complete), and the WSL integration "
             "socket sometimes needs an off/on toggle.",
             "Both are vendor limitations, documented in `docs/CONVENTIONS.md` with the exact remedy rather than "
             "hidden."],
            ["**The `nvidia` RuntimeClass appears late**",
             "k3s creates it a few seconds after the node reports Ready, so an immediate check sees nothing.",
             "Found during rebuild testing and fixed with a wait loop - a race that only appears when you "
             "test from scratch rather than incrementally."],
        ],
        widths=[1.5, 2.4, 2.7],
    )


# =============================================================================
def mistakes(D):
    D.h1("11. Mistakes Made, and What They Cost")
    D.p("Recorded deliberately. A document that only lists successes is not a useful engineering record, "
        "and the recovery is usually more instructive than the error.", color=SLATE)

    D.table(
        ["What went wrong", "Cost", "What prevents a repeat"],
        [
            ["**Pinned tool versions that were stale or fictional.** Helm 3.16 against a current 4.2.4, and "
             "a Trivy version that had never been released - a 404 mid-install.",
             "One failed install run, ~15 minutes",
             "Every pin is now confirmed against the upstream release API, and the download URL checked for "
             "HTTP 200, before it is written into the script."],
            ["**Overwrote a file edited in the wrong place.** The README's GPU section was edited directly "
             "in the repository, then silently reverted by the next sync from the staging directory.",
             "Lost edit, caught by a follow-up check",
             "One source of truth. Edits go to staging and sync forward, never the reverse - and the result "
             "is verified with `grep` afterwards rather than assumed."],
            ["**Cleared a temporary folder that contained my own working directory.** Reclaiming C: by "
             "emptying `%LOCALAPPDATA%\\Temp` deleted the scratch working directory that had been kept there.",
             "**Nothing** - everything had already been committed",
             "Recorded in `docs/CONVENTIONS.md`. The reason it cost nothing is the discipline of committing at each "
             "checkpoint; the same mistake an hour earlier would have been expensive."],
            ["**Trusted a GUI operation without verifying it.** The Docker disk move was reported as done "
             "and was not.",
             "~20 minutes, plus 19.9 GB briefly wasted",
             "Verify state, not the report: check which file the OS has open, and check the registry, rather "
             "than believing a dialog."],
        ],
        widths=[2.55, 1.35, 2.7],
    )
    D.callout("The pattern across all four",
              "Every one is a variant of the same mistake: **believing a report instead of checking the "
              "state.** A version string that was never verified, a sync assumed to be one-directional, a "
              "folder assumed to be disposable, a migration assumed to have run. The habit worth building "
              "is cheap and specific - after any operation that claims success, ask what observable fact "
              "would be true if it really had.", "ok")


# =============================================================================
def explain(D):
    D.h1("12. Design Rationale - Questions Answered")
    D.p("The questions a reviewer is most likely to ask about this milestone, and the reasoning behind each "
        "answer.")
    _qa(D, [
        ("Why test the GPU before writing any code?",
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
        ("How did you know the Docker migration had not worked?",
         "Because I checked the state rather than the report. Two 19.9 GB files existed; I tested which one "
         "the OS had open with an exclusive file handle, and confirmed against the WSL registry's `BasePath`. "
         "Both said D:. The E: copy was orphaned."),
        ("Why copy 20 GB rather than move it?",
         "To keep a rollback. A move is faster but leaves nothing to fall back to if Docker fails to start "
         "from the new location. Five extra minutes bought a guaranteed recovery path, and I only deleted "
         "the original after verifying the images, the volumes and an unrelated running stack had all "
         "survived."),
        ("Why is the repo inside WSL rather than on the Windows drive?",
         "Performance and correctness. The Windows mount is slow for many small files and does not honour "
         "Unix permission bits, which matters for the age keys and signing material from M2 onward."),
        ("Why pin tool versions?",
         "Reproducibility. `latest` is not a version you can return to. My installer compares the installed "
         "version against the pin and reinstalls only on mismatch, so it is both idempotent and an upgrade "
         "path. I verify each pin exists upstream before committing it - I initially pinned a Trivy version "
         "that had never been released."),
    ])


# =============================================================================
def glossary_and_next(D):
    D.h1("13. Glossary - Terms Introduced in M0")
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
            ["**VHDX**", "The virtual disk file format Windows uses. Both the Ubuntu filesystem and Docker's storage are single .vhdx files."],
            ["**Idempotent**", "Safe to run repeatedly with the same result. The toolchain installer is idempotent."],
            ["**ADR**", "Architecture Decision Record - a one-page note of a decision, the alternatives, and the consequences."],
            ["**Init container**", "A container that must finish successfully before the main one starts. Used from M3 to verify model weights."],
        ],
        widths=[1.35, 5.25],
        size=9.3,
    )

    D.h1("14. Open Items Going Into M1")
    D.table(
        ["Item", "Status", "Action"],
        [
            ["Docker storage capacity", "**Resolved**",
             "Moved to `E:\\WSL\\Docker`; ~77 GB free. M1 is unblocked."],
            ["C: drive headroom", "Improved, still tight",
             "4.6 GB free after reclaiming ~7 GB of caches. Worth a deeper clean-up when convenient - but "
             "**not** by emptying `%LOCALAPPDATA%\\Temp` wholesale."],
            ["Git remote", "Not configured",
             "The repository is local only. A public GitHub repo is needed before M2's CI pipeline."],
            ["No scheduler GPU accounting", "Accepted",
             "Documented in ADR 0002. Revisit only if the project moves to native Linux."],
            ["Docker socket after `wsl --shutdown`", "Known workaround",
             "Toggle `IntegratedWslDistros` off and on. Recorded in `docs/CONVENTIONS.md`."],
        ],
        widths=[1.6, 1.15, 3.85],
    )
    D.spacer(4)
    D.callout("Where M1 goes",
              "**M1 - The inference service (Days 2-4).** vLLM serving Qwen2.5-0.5B on the GPU, and the "
              "first version of `palisade-gateway` in FastAPI with an OpenAI-compatible "
              "`/v1/chat/completions` endpoint. Done when you `curl` the gateway and watch tokens stream "
              "back from your own hardware.", "note")
