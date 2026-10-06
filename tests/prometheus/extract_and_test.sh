#!/usr/bin/env bash
# Extracts alerts.yaml from deploy/observability/prometheus-config.yaml's
# ConfigMap (the one source of truth) and runs promtool's own rule tests
# against it via the pinned prom/prometheus image - no separate copy of
# the rules is ever committed, so this can never drift from what the
# cluster actually loads.
set -euo pipefail
cd "$(dirname "$0")"

python3 -c "
import yaml
d = yaml.safe_load(open('../../deploy/observability/prometheus-config.yaml'))
open('alerts.generated.yaml', 'w').write(d['data']['alerts.yaml'])
"

docker run --rm --entrypoint promtool \
  -v "$(pwd):/tests" -w /tests \
  prom/prometheus:v3.13.4 test rules rules_test.yaml

rm -f alerts.generated.yaml
