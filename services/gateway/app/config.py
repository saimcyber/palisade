"""Gateway configuration - all env-driven, nothing hardcoded.

M1 loaded API keys from a flat list of hashes. M4 (docs/adr/0021) replaces
that with `tenants_json`: the same hashes, now carrying a name, a rate
limit and a token budget - the static facts about a tenant. The mutable
state (requests this minute, tokens used this window) lives in Redis,
reached at `redis_url`.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PALISADE_", env_file=".env")

    # Where the real model lives. Defaults to the in-cluster Service name
    # (k8s/vllm.yaml) so the container works unmodified in Kubernetes;
    # docker-compose.yml overrides it for the host-Docker profile.
    upstream_base_url: str = "http://vllm:8000"
    upstream_timeout_seconds: float = 60.0

    # The only model the gateway will ever forward to - see policy.py and
    # docs/adr/0006-server-side-request-policy.md. Callers cannot select a
    # different one; this also lines up with --served-model-name in
    # k8s/vllm.yaml and the compose file.
    served_model_name: str = "palisade-small"

    # JSON object: {"<sha256 of the key>": {"name": ..., "rate_limit_per_minute": ...,
    # "token_budget": ...}}. Loaded from env (sourced from a SOPS-encrypted
    # secret, never committed in plaintext). auth.py never sees or stores a
    # raw key - only this map of accepted hashes to tenant facts.
    tenants: str = ""
    default_rate_limit_per_minute: int = 60
    default_token_budget: int = 20_000

    # Where the per-tenant rate-limit and budget counters, and the response
    # cache, live - see tenancy.py and cache.py. Required at runtime; no
    # default pointing at localhost, since a missing Redis must fail
    # loudly rather than silently run with no budgets enforced.
    redis_url: str = "redis://redis:6379/0"

    # Token budgets are a rolling window, not a lifetime cap - see
    # tenancy.py's module docstring for why this is exempt from the
    # no-time-references rule.
    budget_window_seconds: int = 86_400

    # Crude chars-per-token estimate used only for the pre-flight budget
    # check, before real usage numbers exist - a rough guard, not a
    # guaranteed overestimate; see policy.estimate_tokens's docstring for
    # the known case where it can undershoot.
    estimate_chars_per_token: float = 3.0

    response_cache_ttl_seconds: int = 300

    max_prompt_chars: int = 8_000

    # Server-side clamps - see policy.py. A caller can ask for less, never
    # more.
    max_tokens_ceiling: int = 512

    # Qwen3 emits a <think>...</think> block by default (confirmed in the
    # M1 Task 2 spike) unless a caller explicitly opts back in.
    default_enable_thinking: bool = False

    # Bounds concurrent in-flight calls to vLLM (ADR 0005: one replica, no
    # autoscaling - this is the whole queue-depth story). Past this many
    # requests already waiting on the model, a new one is shed with 503
    # rather than queued indefinitely behind work the GPU cannot speed up -
    # see docs/adr/0024-load-shedding.md and M5's saturation test for the
    # number this was tuned against.
    max_in_flight_upstream_requests: int = 8

    log_level: str = "INFO"


settings = Settings()
