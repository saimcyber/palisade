# =============================================================================
#  Palisade - a secure, self-hosted LLM inference platform
#  Run `make help` to see everything available.
# =============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# --- configuration -----------------------------------------------------------
CLUSTER    ?= palisade
K3S_TAG    ?= v1.31.5-k3s1
K3S_IMAGE  ?= palisade/k3s-nvidia:$(K3S_TAG)
CTX        := k3d-$(CLUSTER)

# Colours (disabled when not a TTY)
ifneq (,$(findstring xterm,$(TERM)))
  C := \033[36m
  G := \033[32m
  Y := \033[33m
  R := \033[0m
else
  C :=
  G :=
  Y :=
  R :=
endif

.PHONY: help doctor tools k3s-image up up-lite up-full down nuke \
        gpu-check cluster-info kubeconfig test lint fmt clean

# --- meta --------------------------------------------------------------------

help: ## Show this help
	@echo ""
	@echo -e "  $(G)Palisade$(R) - make targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  $(C)%-16s$(R) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "  Cluster: $(Y)$(CLUSTER)$(R)   Profile targets: up-lite / up-full"
	@echo ""

doctor: ## Verify every required tool is installed and the GPU is reachable
	@bash scripts/doctor.sh

tools: ## Install the full toolchain (idempotent)
	@bash scripts/install-tools.sh

# --- cluster lifecycle -------------------------------------------------------

k3s-image: ## Build the custom k3s node image with the NVIDIA container runtime
	@bash scripts/build-k3s-image.sh

up: up-lite ## Alias for up-lite

up-lite: ## Create the cluster + GPU support (fits comfortably in 16GB)
	@PROFILE=lite bash scripts/cluster-up.sh

up-full: ## Create the cluster + Argo CD + observability (heavier)
	@PROFILE=full bash scripts/cluster-up.sh

down: ## Delete the cluster (images and volumes are kept)
	@bash scripts/cluster-down.sh

nuke: ## Delete the cluster AND its registry/volumes
	@bash scripts/cluster-down.sh --purge

kubeconfig: ## Point kubectl at this cluster
	@k3d kubeconfig merge $(CLUSTER) --kubeconfig-switch-context >/dev/null
	@echo "kubectl context is now $(CTX)"

cluster-info: ## Show nodes, GPU capacity and running pods
	@kubectl --context $(CTX) get nodes -o wide
	@echo ""
	@kubectl --context $(CTX) get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}' \
		| awk 'BEGIN{printf "%-24s %s\n","NODE","ALLOCATABLE GPUs"} {printf "%-24s %s\n", $$1, ($$2==""?"0":$$2)}'
	@echo ""
	@kubectl --context $(CTX) get pods -A

# --- verification ------------------------------------------------------------

gpu-check: ## Run a pod that must see the RTX 3050 (M0 acceptance test)
	@bash scripts/gpu-check.sh

test: ## Run the unit test suite
	@if [ -d services/gateway/tests ]; then \
		cd services/gateway && python3 -m pytest -q; \
	else \
		echo "no tests yet - added in M1"; \
	fi

lint: ## Lint everything that has a linter
	@pre-commit run --all-files || true

fmt: ## Format code in place
	@pre-commit run --all-files --hook-stage manual || true

clean: ## Remove local build artefacts
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned"
