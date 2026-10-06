"""Tiny Prometheus exporter around `nvidia-smi` - the whole reason this
image exists (see the Dockerfile's header). No dependencies beyond the
standard library: this is a few GPU numbers behind an HTTP server, not an
application.
"""

from __future__ import annotations

import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

QUERY_FIELDS = ["utilization.gpu", "memory.used", "memory.total", "temperature.gpu"]

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _collect() -> tuple[bool, str]:
    """Returns (success, prometheus-text). Never raises - a failed
    `nvidia-smi` call is itself a metric (nvidia_smi_last_collect_success),
    not an HTTP error."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={','.join(QUERY_FIELDS)}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"# collection failed: {exc}\n"

    if result.returncode != 0:
        return (
            False,
            f"# nvidia-smi exited {result.returncode}: {result.stderr.strip()}\n",
        )

    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    body = []
    for index, line in enumerate(lines):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(QUERY_FIELDS):
            continue
        util, mem_used, mem_total, temp = parts
        labels = f'{{index="{index}"}}'
        body.append(f"nvidia_smi_utilization_gpu_ratio{labels} {float(util) / 100:.4f}")
        body.append(
            f"nvidia_smi_memory_used_bytes{labels} {float(mem_used) * 1024 * 1024:.0f}"
        )
        body.append(
            f"nvidia_smi_memory_total_bytes{labels} {float(mem_total) * 1024 * 1024:.0f}"
        )
        body.append(f"nvidia_smi_temperature_celsius{labels} {float(temp):.1f}")
    return True, "\n".join(body) + "\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # quiet - stdout is for errors only
        pass

    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        success, metrics_body = _collect()
        payload = (
            "# HELP nvidia_smi_last_collect_success Whether the most recent "
            "nvidia-smi call succeeded.\n"
            "# TYPE nvidia_smi_last_collect_success gauge\n"
            f"nvidia_smi_last_collect_success {1 if success else 0}\n" + metrics_body
        )
        encoded = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    HTTPServer(("0.0.0.0", 9835), Handler).serve_forever()


if __name__ == "__main__":
    main()
