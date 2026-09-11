# Documentation

One write-up per milestone, recording how I built that part of Palisade: what I
did, what went wrong, where I deviated from the plan, the limitations of the
result, and why I picked each tool over its alternatives.

Most project docs describe the finished state and quietly delete the route taken
to get there. I'm doing the opposite here — the dead ends and the reasoning are
the point, because that's the part I actually learned from. Every idea appears
twice: once in **plain language**, once **technically**, so it stays followable
whether or not Kubernetes is already familiar.

## Milestones

| Milestone | Document | Status |
| --- | --- | --- |
| M0 — Foundations | [`M0-Foundations.docx`](M0-Foundations.docx) | Complete |
| M1 — Inference service | [`M1-Inference-Service.docx`](M1-Inference-Service.docx) | Complete |
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

I generate the documents from source so they stay consistent in structure and
styling, and so I fix a mistake once at the source and rebuild rather than
hand-patching a Word file.

```bash
cd documentation/_build
pip install python-docx          # once
python build.py m0               # -> ../M0-Foundations.docx
python build.py --all            # every milestone with a content module
```

| File | Role |
| --- | --- |
| `docx_kit.py` | Shared styling. Changing it restyles every document at once. |
| `build.py` | Milestone → filename mapping and section ordering. |
| `m0.py`, `m1.py`, … | The content of one milestone each. |

> The `.docx` files are committed deliberately. They are a deliverable of the project, not
> a build artefact, and should be readable straight from the repository.

## See also

- [`../docs/adr/`](../docs/adr/) — architecture decision records. ADRs capture a **single
  decision** at the moment it is made; these documents capture a **whole milestone** after
  the fact. They complement rather than duplicate each other.
