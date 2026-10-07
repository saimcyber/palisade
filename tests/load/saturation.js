// Ramps one tenant's concurrency past the gateway's in-flight ceiling
// (PALISADE_MAX_IN_FLIGHT_UPSTREAM_REQUESTS, default 8 - ADR 0024) to
// prove load shedding actually activates under real saturation, not
// just under the hand-fed values test_loadshed.py exercises.
//
// Runs two places, on purpose (ADR 0025):
//   CI (alert-rules-test.yml's sibling)  -> against tests/load/stub_upstream.py,
//                                           proves the gateway's own logic holds
//                                           under concurrency - no GPU involved.
//   Locally, by hand                      -> against the real cluster and the
//                                           real RTX 3050, for the numbers that
//                                           actually back docs/SLO.md.
//
// Run locally:
//   kubectl -n palisade port-forward svc/palisade-gateway 18080:8080 &
//   PALISADE_GATEWAY_URL=http://localhost:18080 \
//     PALISADE_TENANT_A_KEY=... k6 run tests/load/saturation.js
import http from "k6/http";
import { Counter, Rate } from "k6/metrics";

const BASE_URL = __ENV.PALISADE_GATEWAY_URL || "http://localhost:8080";
const TENANT_A_KEY = __ENV.PALISADE_TENANT_A_KEY;

export const shed503 = new Counter("saturation_503_shed");
export const errorRate = new Rate("saturation_error_rate");

export const options = {
  scenarios: {
    saturate: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "15s", target: 30 },
        { duration: "20s", target: 30 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    // The acceptance claim: shedding activates under real saturation,
    // and nothing above 503 (no 500s, no crashes) - a saturated gateway
    // degrades on purpose, it doesn't fall over.
    saturation_503_shed: ["count>0"],
    saturation_error_rate: ["rate<0.02"],
  },
};

export default function () {
  const body = JSON.stringify({
    messages: [
      { role: "user", content: `saturation probe ${__VU}-${__ITER}` },
    ],
    max_tokens: 16,
  });
  const res = http.post(`${BASE_URL}/v1/chat/completions`, body, {
    headers: {
      Authorization: `Bearer ${TENANT_A_KEY}`,
      "Content-Type": "application/json",
    },
  });
  if (res.status === 503) {
    shed503.add(1);
  }
  // Only a genuine server error counts against the error rate - 429s
  // (budget/rate-limit) and 503 (load shed) are all correct, deliberate
  // responses, not failures.
  errorRate.add(res.status >= 500 && res.status !== 503);
}
