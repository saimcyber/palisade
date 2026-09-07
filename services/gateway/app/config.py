"""Gateway configuration - all env-driven, nothing hardcoded.

M1 loads API keys from an env var (see auth.py for why only their hashes are
kept in memory). M4 moves key storage to Redis; this module's shape does not
need to change for that - only where auth.py looks the hash up.
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

    # Comma-separated SHA-256 hashes of accepted API keys, loaded from env
    # rather than committed anywhere. auth.py never sees or stores a raw key.
    api_key_hashes: str = ""

    # Server-side clamps - see policy.py. A caller can ask for less, never
    # more.
    max_tokens_ceiling: int = 512

    # Qwen3 emits a <think>...</think> block by default (confirmed in the
    # M1 Task 2 spike) unless a caller explicitly opts back in.
    default_enable_thinking: bool = False

    log_level: str = "INFO"


settings = Settings()
