# 23. Observability stack: plain manifests, no Operator, no Alertmanager

- **Status:** Accepted

## Context

M4 calls for Prometheus, Grafana, a GPU exporter, four dashboards and a set
of alert rules - "slim enough to fit alongside the workload" (the plan's
own words), on a machine with 16 GB of RAM, WSL2 capped at 10 GB, already
running vLLM, the gateway, Redis, Argo CD and Kyverno.

Three real options existed for how to ship this: the `kube-prometheus-stack`
Helm chart (the default choice almost everywhere), a hand-rolled set of
plain manifests, or skipping some pieces entirely.

## Decision

**Plain manifests in `deploy/observability/`, synced by their own Argo CD
Application** (`deploy/argocd/apps/observability.yaml`) - not
`kube-prometheus-stack`. That chart bundles the Prometheus Operator, its
CRDs, node-exporter (wants host access the Kyverno baseline would have to
carve an exception for) and Alertmanager, none of which this milestone's
four fixed, known-in-advance targets need. Four small Deployments plus a
handful of ConfigMaps is less total YAML than one Operator's CRDs, and —
unlike the chart — keeps every dashboard and alert rule a plain,
diffable file in Git rather than a Helm value.

**GPU exporter: a `nvidia-smi` wrapper, not `dcgm-exporter`.** The NVIDIA
device plugin cannot work under WSL2 (ADR 0002) because it depends on
NVML against `/dev/dxg`; `dcgm-exporter` sits on the identical NVML layer
and would hit the identical wall. A pod that calls `nvidia-smi` through
the already-proven CDI path (`make gpu-check`) has no such dependency.

The third-party `utkuozdemir/nvidia_gpu_exporter` was tried first and
replaced with a project-built one (`docker/gpu-exporter/` - a few dozen
lines of `subprocess` + `http.server`, no dependencies) after two
confirmed-live findings: that image ships no shell and no `/usr/bin` for
CDI's injection hook to write `nvidia-smi` into, and - the part a
full-filesystem rebuild alone didn't fix - `nvidia-container-runtime`'s
hook only injects the "utility" driver capability (which carries
`nvidia-smi`) when `NVIDIA_DRIVER_CAPABILITIES` says to. `nvidia/cuda`-
based images (`k8s/gpu-check.yaml`'s image, for instance) set that by
default; nothing else does. The project's own exporter sets it
explicitly, is built on the same `python:3.12-slim` digest already
trusted for the gateway, and is built, scanned, signed and pushed by its
own workflow (`gpu-exporter-image.yml`), the same pipeline shape as every
other image in this project rather than an unverified pull from Docker
Hub.

**No PersistentVolumeClaim on Prometheus.** A 6-hour retention window on an
`emptyDir` is enough to drive four live dashboards and evaluate alert
rules; surviving a pod restart with history intact is not a goal this
milestone needs, and a PVC here would re-open the exact
`WaitForFirstConsumer` sync-wave question ADR 0017 already closed once.

**No Alertmanager deployed.** The five rules in `prometheus-config.yaml`'s
`alerts.yaml` are real: `promtool check rules`-verified for syntax, and
behaviour-tested against synthetic input series with `promtool test rules`
(`tests/prometheus/`, run via `extract_and_test.sh`, which extracts the
ConfigMap's own `alerts.yaml` rather than keeping a second copy of it) -
covering every rule's firing path, plus explicit negative cases for the
two `for:`-qualified ones. This portfolio-scale platform still has no
on-call pager for them to page, though - running
Alertmanager with no real receiver configured would be theatre. The rules
fire and are visible in Prometheus's own `/alerts` page; wiring a receiver
(Slack, email, PagerDuty) is a config change to this one component, not an
architecture change, whenever there's a real destination for it.

**Decoupled from the core workload chain.** `palisade-observability`'s own
sync-wave is `"2"` - strictly *after* `palisade` (wave 1) reports Healthy,
never gating it. `palisade-secrets` (wave 0) and `palisade-policies`
(wave -1) are allowed to block the gateway and vLLM from deploying because
that coupling is the point (ADR 0020); a stalled Grafana image pull must
never be able to do the same. Its one SOPS-encrypted secret (Grafana's
admin password) lives in its own directory,
`deploy/observability-secrets/`, synced by its own Application
(`palisade-observability-secrets`, wave `"2"`) - not in `deploy/secrets/`
(that would put it back under `palisade-secrets`'s wave-0 gate) and not
alongside the rest of `deploy/observability/` either, for a second,
unrelated reason: the sops-decrypt CMP's `generate` command
(`argocd-values.yaml`) concatenates every `*.yaml` file in a source path
with no document separator between them. `deploy/secrets/` has only ever
held one file, so this never mattered before; `deploy/observability/`
holds a dozen, so its one encrypted secret needs a directory of its own.

**Deployed unconditionally, not gated behind `up-full`.** The project
plan's own risk table named "running observability only when working on
it" as the RAM mitigation, written before any real number existed. A
measurement taken before this milestone's Redis, Prometheus, Grafana,
kube-state-metrics and the GPU exporter were added - 5.4 GiB used, 4.3 GiB
available, inside the WSL2 VM's 9.7 GiB cap, with vLLM, the gateway, Argo
CD and Kyverno already running - showed enough headroom for all five at
their configured limits (under 1 GiB combined) without the toggle the plan
assumed it would need. `up-full` is kept as a documented alias rather than
removed, in case a future, heavier addition needs the distinction back.

**Static scrape targets, not Kubernetes service discovery.** Five fixed
targets (gateway, vLLM, kube-state-metrics, the GPU exporter, Kyverno)
never change shape here; `kubernetes_sd_configs` would need Prometheus
itself to hold a ClusterRole to list/watch services and endpoints
cluster-wide, for a convenience this cluster doesn't need. The one
exception, `kube-state-metrics`, needs its own API access regardless of
how Prometheus finds it - that ClusterRole is scoped to `pods` only, the
one resource the restart-loop alert actually reads.

## Consequences

- Scraping is inbound to vLLM and the gateway, so it never touches the
  "no egress whatsoever from vLLM" claim (ADR 0014) - but vLLM's
  NetworkPolicy did need a second `ingress` rule for the `monitoring`
  namespace, alongside the existing gateway-only one, or Prometheus's
  scrape would fail silently with every vLLM target reporting `down`.
- `nvidia_smi_utilization_gpu_ratio` and friends are a specific exporter's
  metric names, not a Prometheus standard - if the GPU dashboard's panels
  come back empty, check the exporter's own `/metrics` output before
  assuming the dashboard is wrong.
- **Fixed and confirmed live**: the GPU exporter's nvidia-smi panels now
  populate (`nvidia_smi_last_collect_success` is `1`, real utilisation/
  VRAM/temperature values observed). Took two fixes, not one - a
  full-filesystem base image (necessary, since the original image had
  nowhere for the injection hook to write) and `NVIDIA_DRIVER_CAPABILITIES
  =utility` (the actual trigger for the hook to inject `nvidia-smi` at
  all) - see the Dockerfile's header in `docker/gpu-exporter/` for the
  full investigation and what was tried and disproved before the real
  cause was found by diffing against the known-working `gpu-check` Job.
- No Alertmanager means no deduplication, grouping, or silencing - five
  rules firing in a tight loop produces five separate alert states in
  Prometheus, not one grouped notification. Acceptable here; the first
  thing a real receiver integration would need to reconsider.
