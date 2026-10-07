"""Stand-in for vLLM, used only in CI's load test (ADR 0025) - returns a
fixed completion instantly, with no model and no GPU, so the gateway's
own logic (rate limiting, budget reservation, the cache, load shedding)
gets exercised under real concurrency on infrastructure GitHub owns.
Never used for anything that claims to measure real throughput or
latency - that run only ever happens locally, against the real GPU.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

USAGE = {"prompt_tokens": 10, "completion_tokens": 5}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/v1/models":
            self._json(200, {"object": "list", "data": []})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            chunk = {"choices": [{"delta": {"content": "stub"}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            usage_chunk = {"choices": [], "usage": USAGE}
            self.wfile.write(f"data: {json.dumps(usage_chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            self._json(
                200,
                {
                    "id": "stub",
                    "choices": [{"message": {"content": "stub"}}],
                    "usage": USAGE,
                },
            )

    def _json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
