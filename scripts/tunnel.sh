#!/usr/bin/env bash
# =============================================================================
#  Palisade - public demo tunnel (Cloudflare Quick Tunnel)
#
#  Puts the gateway on a public https://<random>.trycloudflare.com URL, on
#  demand, for as long as the operator wants it there - and no longer.
#
#  Deliberately NOT part of the platform (docs/adr/0026):
#    - Off by default. The cluster never exposes itself; a person runs this.
#    - Points at the real Traefik Ingress, so the public path gets exactly the
#      Ingress allowlist (/v1/*, /healthz) - /metrics, /docs, /readyz,
#      Grafana and Prometheus are unreachable through it by construction.
#    - Hand out ONLY the tenant-public key: 10 requests/minute, 3000 tokens.
#    - Quick Tunnels need no Cloudflare account and no token, and the URL is
#      new every time - which is the point: nothing to leak, nothing to revoke.
#
#  Usage:
#    bash scripts/tunnel.sh up       # start; prints the public URL
#    bash scripts/tunnel.sh status   # is it up, and does the public URL answer
#    bash scripts/tunnel.sh down     # stop it
#    bash scripts/tunnel.sh url      # print the current URL only
# =============================================================================
set -euo pipefail

LOCAL_URL="${LOCAL_URL:-http://localhost:8080}"
HOST_HEADER="${HOST_HEADER:-palisade.local}"
DEMO_KEY_FILE="${DEMO_KEY_FILE:-$HOME/.config/palisade/demo-tenant-c-key}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/palisade/tunnel"
PID_FILE="$STATE/cloudflared.pid"
LOG_FILE="$STATE/cloudflared.log"
URL_FILE="$STATE/url"

GREEN='\033[32m'; YEL='\033[33m'; RED='\033[31m'; CYA='\033[36m'; RST='\033[0m'
ok()   { printf '  %bok%b   %s\n' "$GREEN" "$RST" "$*"; }
note() { printf '  %bnote%b %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %bfail%b %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n%b==>%b %s\n' "$CYA" "$RST" "$*"; }

running() { [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

up() {
  step "Preconditions"
  command -v cloudflared >/dev/null || die "cloudflared not installed - run: make tools"
  ok "cloudflared $(cloudflared --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  [ -s "$DEMO_KEY_FILE" ] || die "no demo key at $DEMO_KEY_FILE - tenant-public's raw key is required"
  ok "tenant-public key present (10 req/min, 3000-token budget)"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $HOST_HEADER" "$LOCAL_URL/healthz" || true)
  [ "$code" = "200" ] || die "local Ingress $LOCAL_URL (Host: $HOST_HEADER) /healthz returned $code - is the cluster up?"
  ok "local Ingress healthy"
  if running; then
    note "already running (pid $(cat "$PID_FILE")) at $(cat "$URL_FILE" 2>/dev/null)"
    return 0
  fi

  step "Starting the Quick Tunnel"
  mkdir -p "$STATE"
  # Quick Tunnels carry no uptime guarantee, and provisioning one can take
  # longer than cloudflared's own fixed 15s request timeout - seen live (an
  # 18s provisioning call, "context deadline exceeded"). A bounded retry, not
  # an open-ended loop: three attempts, then a clear failure.
  local url="" attempt reason=""
  for attempt in 1 2 3; do
    : > "$LOG_FILE"
    nohup cloudflared tunnel --no-autoupdate \
      --url "$LOCAL_URL" --http-host-header "$HOST_HEADER" \
      >"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    for _ in $(seq 1 60); do
      # api.trycloudflare.com is the endpoint cloudflared *requests* a tunnel
      # from - it also appears in the log when that request fails, so it must
      # never be mistaken for the assigned URL.
      url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_FILE" \
              | grep -v '^https://api\.trycloudflare\.com$' | head -1 || true)
      [ -n "$url" ] && break 2
      if grep -q 'failed to request quick Tunnel' "$LOG_FILE"; then
        reason=$(grep 'failed to request quick Tunnel' "$LOG_FILE" | tail -1)
        break
      fi
      running || { reason="cloudflared exited early"; break; }
      sleep 1
    done
    down >/dev/null
    note "attempt $attempt/3 failed: ${reason#*: }"
    sleep 5
  done
  [ -n "$url" ] || die "no tunnel after 3 attempts - Cloudflare's Quick Tunnel service may be degraded (see $LOG_FILE)"
  echo "$url" > "$URL_FILE"
  ok "assigned $url"

  # A fresh trycloudflare hostname can take a few seconds to resolve and route.
  step "Waiting for the public URL to answer"
  for _ in $(seq 1 45); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url/healthz" || true)
    [ "$code" = "200" ] && break
    sleep 2
  done
  [ "$code" = "200" ] || note "public /healthz still returned '$code' - DNS may need a little longer; try: make tunnel-status"
  [ "$code" = "200" ] && ok "public /healthz -> 200"

  printf '\n%bPublic demo endpoint:%b %s\n' "$GREEN" "$RST" "$url"
  cat <<EOF

  Try it (hands out only the capped tenant-public key):

    curl $url/v1/chat/completions \\
      -H "Authorization: Bearer \$(cat $DEMO_KEY_FILE)" \\
      -H "Content-Type: application/json" \\
      -d '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":32}'

  Stop it with: make tunnel-down
EOF
}

status() {
  if running; then
    local url code
    url=$(cat "$URL_FILE" 2>/dev/null || echo "?")
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url/healthz" || true)
    ok "running (pid $(cat "$PID_FILE")) at $url - public /healthz -> $code"
  else
    note "not running"
    return 1
  fi
}

down() {
  if running; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    for _ in $(seq 1 10); do running || break; sleep 1; done
    if running; then kill -9 "$(cat "$PID_FILE")" 2>/dev/null || true; fi
    ok "tunnel stopped"
  else
    note "no tunnel was running"
  fi
  rm -f "$PID_FILE" "$URL_FILE"
}

case "${1:-}" in
  up) up ;;
  status) status ;;
  down) down ;;
  url) if [ -f "$URL_FILE" ]; then cat "$URL_FILE"; else echo "no tunnel running" >&2; exit 1; fi ;;
  *) echo "usage: $0 {up|status|down|url}" >&2; exit 2 ;;
esac
