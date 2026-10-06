// M4's acceptance test, literally: two tenants sending real traffic,
// tenant-b's token budget deliberately tiny (500, set in
// deploy/secrets/gateway-secret.enc.yaml) so it hits its cap inside a
// short run while tenant-a (50,000) is unaffected. Each request carries a
// unique prompt (the VU/iteration number) rather than one fixed string -
// an identical prompt would cache-hit after the first call, which this
// gateway still bills to budget correctly (ADR 0021) but would make a
// weaker demo of real GPU-driven spend diverging between tenants.
//
// constant-arrival-rate, not constant-vus: a fixed 1 req/s per tenant
// means tenant-b's own flood of near-instant 429s after it exhausts its
// budget can never crowd out tenant-a's traffic on the gateway's single
// replica (ADR 0005) - the two tenants' request rates stay independent of
// each other and of how fast either one gets answered, which is the only
// way "the other is unaffected" is actually a meaningful claim rather
// than an artifact of which VU happened to get scheduled.
//
// Run against a port-forwarded gateway:
//   kubectl -n palisade port-forward svc/palisade-gateway 8080:8080 &
//   PALISADE_TENANT_A_KEY=... PALISADE_TENANT_B_KEY=... k6 run tests/load/two-tenants.js
import http from "k6/http";
import { Counter, Rate } from "k6/metrics";

const BASE_URL = __ENV.PALISADE_GATEWAY_URL || "http://localhost:8080";
const TENANT_A_KEY = __ENV.PALISADE_TENANT_A_KEY;
const TENANT_B_KEY = __ENV.PALISADE_TENANT_B_KEY;

export const tenantBBudgetExhausted = new Counter("tenant_b_budget_exhausted");
export const tenantASuccessRate = new Rate("tenant_a_success_rate");

export const options = {
  scenarios: {
    tenant_a: {
      executor: "constant-arrival-rate",
      exec: "callAsTenantA",
      rate: 1,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 5,
    },
    tenant_b: {
      executor: "constant-arrival-rate",
      exec: "callAsTenantB",
      rate: 1,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 5,
    },
  },
  // The actual acceptance assertion: tenant-b must get budget-rejected at
  // least once, and tenant-a's success rate must stay effectively
  // unaffected, in the same run - k6 thresholds, so a failure here
  // reports the normal way (`k6 run` exits non-zero) rather than a thrown
  // exception.
  thresholds: {
    tenant_b_budget_exhausted: ["count>0"],
    tenant_a_success_rate: ["rate>0.99"],
  },
};

function chatRequest(apiKey) {
  const body = JSON.stringify({
    messages: [
      {
        role: "user",
        content: `Say a short fact about VU ${__VU} iteration ${__ITER}.`,
      },
    ],
    max_tokens: 32,
  });
  return http.post(`${BASE_URL}/v1/chat/completions`, body, {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
  });
}

export function callAsTenantA() {
  const res = chatRequest(TENANT_A_KEY);
  tenantASuccessRate.add(res.status === 200);
}

export function callAsTenantB() {
  const res = chatRequest(TENANT_B_KEY);
  if (res.status === 429 && res.json("error") === "budget_exhausted") {
    tenantBBudgetExhausted.add(1);
  }
}
