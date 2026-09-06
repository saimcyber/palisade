#!/usr/bin/env bash
# Delete the local cluster. Images are kept unless --purge is passed.
set -euo pipefail

CLUSTER="${CLUSTER:-palisade}"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

if k3d cluster list 2>/dev/null | awk '{print $1}' | grep -qx "$CLUSTER"; then
  k3d cluster delete "$CLUSTER"
  echo "cluster '$CLUSTER' deleted"
else
  echo "cluster '$CLUSTER' does not exist"
fi

if [ "$PURGE" = "1" ]; then
  docker volume ls -q --filter "name=k3d-${CLUSTER}" | xargs -r docker volume rm
  docker image rm -f "palisade/k3s-nvidia:${K3S_TAG:-v1.36.4-k3s1}" 2>/dev/null || true
  echo "purged volumes and node image"
fi
