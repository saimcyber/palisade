# Learning log

One Word document per milestone, recording what was built and — more importantly — what
went wrong, what was decided differently from the plan, and why each tool was chosen over
its alternatives.

These are written for two readers at once: **future me**, revising before an interview,
and **someone else** trying to understand the reasoning without having lived through it.
Every idea therefore appears twice — once in plain language, once technically.

## Documents

| Milestone | Document | Status |
| --- | --- | --- |
| M0 — Foundations | [`M0-Foundations.docx`](M0-Foundations.docx) | Complete |
| M1 — Inference service | `M1-Inference-Service.docx` | Pending |
| M2 — Supply chain & CI/CD | `M2-Supply-Chain-CICD.docx` | Pending |
| M3 — Kubernetes, GitOps & policy | `M3-Kubernetes-GitOps-Policy.docx` | Pending |
| M4 — Platform & observability | `M4-Platform-Observability.docx` | Pending |
| M5 — Resilience & proof | `M5-Resilience-Proof.docx` | Pending |

## What every document covers

1. What the milestone was for
2. Where things stood before it
3. Decisions taken up front, with the alternatives rejected
4. What was actually built
5. A deep dive on the hardest problem of the milestone
6. Deviations from the plan, and why
7. Tool choices: chosen vs rejected
8. Limitations of the result
9. What you should be able to explain (rehearsed interview answers)
10. Glossary of terms the milestone introduced
11. Open items going into the next milestone

## Regenerating

The documents are generated from source so they stay consistent and can be corrected and
rebuilt rather than hand-edited.

```bash
cd learning/_build
pip install python-docx          # once
python build.py m0               # -> ../M0-Foundations.docx
python build.py --all            # every milestone with a content module
```

- `docx_kit.py` — shared styling. Changing it restyles every document at once, which is
  the point: they should be indistinguishable in form.
- `build.py` — milestone → filename mapping and section ordering.
- `m0.py`, `m1.py`, … — the content of one milestone each.

> The `.docx` files are committed deliberately. They are a deliverable of the project, not
> a build artefact, and they should be readable straight from the repository.
