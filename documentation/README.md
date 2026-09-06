# Documentation

One document per milestone, recording how Palisade was built: what was done, what went
wrong, what was decided differently from the plan, the limitations of the result, and why
each tool was chosen over its alternatives.

Most project documentation describes the finished state and quietly deletes the route
taken to get there. These do the opposite — the dead ends and the reasoning are the point.
Every idea appears twice: once in **plain language**, once **technically**, so the
documents are readable whether or not you already know Kubernetes.

## Milestones

| Milestone | Document | Status |
| --- | --- | --- |
| M0 — Foundations | [`M0-Foundations.docx`](M0-Foundations.docx) | Complete |
| M1 — Inference service | `M1-Inference-Service.docx` | Pending |
| M2 — Supply chain & CI/CD | `M2-Supply-Chain-CICD.docx` | Pending |
| M3 — Kubernetes, GitOps & policy | `M3-Kubernetes-GitOps-Policy.docx` | Pending |
| M4 — Platform & observability | `M4-Platform-Observability.docx` | Pending |
| M5 — Resilience & proof | `M5-Resilience-Proof.docx` | Pending |

## Structure of each document

1. What the milestone was for
2. Where things stood before it
3. Decisions taken up front, with the alternatives rejected
4. What was actually built
5. A deep dive on the hardest problem of the milestone
6. Deviations from the plan, and why
7. Tool choices: chosen vs rejected
8. Limitations of the result
9. Design rationale — the questions a reviewer would ask
10. Glossary of terms the milestone introduced
11. Open items going into the next milestone

## Regenerating

The documents are generated from source so they stay consistent in structure and styling,
and so a mistake is corrected at the source and rebuilt rather than patched by hand.

```bash
cd documentation/_build
pip install python-docx          # once
python build.py m0               # -> ../M0-Foundations.docx
python build.py --all            # every milestone with a content module
```

| File | Role |
| --- | --- |
| `docx_kit.py` | Shared styling. Changing it restyles every document at once — which is the point. |
| `build.py` | Milestone → filename mapping and section ordering. |
| `m0.py`, `m1.py`, … | The content of one milestone each. |

> The `.docx` files are committed deliberately. They are a deliverable of the project, not
> a build artefact, and should be readable straight from the repository.

## See also

- [`../docs/adr/`](../docs/adr/) — architecture decision records. ADRs capture a **single
  decision** at the moment it is made; these documents capture a **whole milestone** after
  the fact. They complement rather than duplicate each other.
