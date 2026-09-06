# -*- coding: utf-8 -*-
"""
Build a Palisade engineering document (one per milestone).

    python build.py m0          -> ../M0-Foundations.docx
    python build.py --all       -> every milestone module found

One module per milestone (m0.py, m1.py, ...). Each module exposes an ordered
list of section functions via SECTIONS, or is discovered by convention below.

Requires: pip install python-docx
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from docx_kit import Doc  # noqa: E402

# milestone key -> (module, output filename, footer label)
MILESTONES = {
    "m0": ("m0", "M0-Foundations.docx", "Palisade Engineering Log - M0 Foundations"),
    "m1": ("m1", "M1-Inference-Service.docx", "Palisade Engineering Log - M1 Inference Service"),
    "m2": ("m2", "M2-Supply-Chain-CICD.docx", "Palisade Engineering Log - M2 Supply Chain & CI/CD"),
    "m3": ("m3", "M3-Kubernetes-GitOps-Policy.docx", "Palisade Engineering Log - M3 Kubernetes, GitOps & Policy"),
    "m4": ("m4", "M4-Platform-Observability.docx", "Palisade Engineering Log - M4 Platform & Observability"),
    "m5": ("m5", "M5-Resilience-Proof.docx", "Palisade Engineering Log - M5 Resilience & Proof"),
}

# The order sections are rendered in. Any missing function is skipped, so a
# milestone module only has to implement the sections that apply to it.
SECTION_ORDER = [
    "cover",
    "what_m0_was_for", "what_it_was_for",
    "starting_point",
    "decisions",
    "what_was_built",
    "gpu_problem",          # M0-specific deep dive
    "deep_dive",            # generic slot for later milestones
    "deviations",
    "tool_choices",
    "limitations",
    "explain",
    "glossary_and_next",
]


def build(key):
    if key not in MILESTONES:
        raise SystemExit(f"unknown milestone '{key}'. known: {', '.join(MILESTONES)}")
    mod_name, out_name, footer = MILESTONES[key]
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        raise SystemExit(f"no content module '{mod_name}.py' yet - write it first")

    D = Doc()
    rendered = []
    for fn_name in SECTION_ORDER:
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            fn(D)
            rendered.append(fn_name)

    D.footer_page_numbers(footer)
    cp = D.d.core_properties
    cp.title = footer
    cp.author = "Saim Zaib"
    cp.subject = "Palisade - a secure, self-hosted LLM inference platform"
    cp.keywords = "DevOps, DevSecOps, Kubernetes, GPU, engineering log"

    out = os.path.join(OUT_DIR, out_name)
    D.save(out)
    print(f"wrote {out}")
    print(f"  sections: {', '.join(rendered)}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "--all":
        for k in MILESTONES:
            if os.path.exists(os.path.join(HERE, MILESTONES[k][0] + ".py")):
                build(k)
    else:
        for k in args:
            build(k)
