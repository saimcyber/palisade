# 14. Default-deny, with egress as the deliberate claim - not ingress

- **Status:** Accepted

## Context

The plan's own wording is specific: "gateway to vLLM and Redis only... no
egress whatsoever from vLLM." That's an egress claim. Nothing in the plan
asks for ingress lockdown to the gateway (which would mean reasoning about
the exact identity of whatever ingress controller is installed), and
conflating the two would make a broader, less precise claim than the one
actually being made.

## Decision

**`default-deny-all`** (empty `podSelector`, both `Ingress` and `Egress`,
no rules) is the floor every other NetworkPolicy in `deploy/policies/`
carves a specific exception out of - nothing is reachable, in or out,
except what's named explicitly.

**Ingress to the gateway is left open by source.** The ingress
controller's exact namespace and labels vary by how it's installed and
aren't the thing this milestone is making a claim about; constraining
north-south traffic here would just be a different, unstated claim wearing
the same policy.

**Egress is where the real claims live, one policy per workload:**

- The gateway may reach DNS (needed to resolve `vllm` as a Service name at
  all once egress defaults to deny), vLLM on port 8000, and Redis on port
  6379 - inert today (M4 introduces Redis), effective the moment it
  exists, with no policy edit needed then.
- vLLM's `NetworkPolicy` lists only `Ingress` in `policyTypes`, from the
  gateway, on port 8000 - and never adds an `egress:` block of its own.
  Egress stays exactly what `default-deny-all` already says: none.
- The model-verify Job (ADR 0012) gets its own `NetworkPolicy`: DNS plus
  outbound HTTPS, nothing else - and this is the entire reason it's a
  separate pod rather than a vLLM `initContainer`. `NetworkPolicy` applies
  at the pod level; it cannot grant one container in a pod egress while
  denying it to another container in the *same* pod. Splitting the
  verifier into its own pod is what makes "vLLM has zero egress" and "the
  verifier can reach Hugging Face" simultaneously true statements instead
  of a contradiction.

## Consequences

- "No egress whatsoever from vLLM" is now checkable by reading exactly one
  file (`networkpolicy-vllm.yaml`) and confirming it, and can be
  demonstrated live: a shell into the vLLM pod attempting any outbound
  connection should fail, and that attempt is worth recording as evidence
  alongside the signature-refusal demonstration.
- DNS egress is granted broadly (any pod, any namespace, port 53) rather
  than pinned to CoreDNS's exact labels, which do vary by cluster
  distribution. A reasonable, common trade-off for a policy whose real
  claim is about application traffic, not about DNS infrastructure this
  project doesn't operate.
