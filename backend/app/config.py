"""Central configuration — env vars only, no secrets in code."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CineGuard API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # Gemini / Google Cloud (ADK). Empty = local heuristic mode.
    gemini_api_key: str = ""
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 60
    gemini_max_output_tokens: int = 8192
    # Structured-output parse retries (malformed JSON only, not auth errors).
    gemini_parse_attempts: int = 2

    # Persistence: local SQLite file. Env CINEGUARD_DB_PATH wins; a
    # sqlite: DATABASE_URL is honored; Postgres DDL is in migrations/.
    cineguard_db_path: str = ""

    # Parallel robustness: bounded retries with backoff on transient failures.
    parallel_max_retries: int = 2
    parallel_retry_base_seconds: float = 0.5

    # Input guardrail — single source of truth (mirrors schema max_length).
    # Larger inputs are rejected with a clear error; chunking is a future step.
    max_screenplay_chars: int = 200_000

    # External research — live Parallel Search API when key present,
    # honest not-run otherwise (never fake citations).
    parallel_api_key: str = ""
    parallel_timeout_seconds: int = 20
    parallel_max_results: int = 5
    research_max_queries: int = 6

    # Deterministic readiness scoring (backend-owned, never model-invented).
    readiness_weight_critical: float = 15.0
    readiness_weight_high: float = 5.0
    readiness_weight_medium: float = 2.0
    readiness_weight_low: float = 0.5
    confidence_multiplier_high: float = 1.0
    confidence_multiplier_medium: float = 0.7
    confidence_multiplier_low: float = 0.4
    readiness_ready_at: float = 80.0
    readiness_at_risk_at: float = 60.0
    readiness_high_risk_at: float = 40.0

    database_url: str = ""

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key or self.google_cloud_project)

    @property
    def is_parallel_configured(self) -> bool:
        return bool(self.parallel_api_key)

    def public_status(self) -> dict:
        """Safe status payload — never includes secret values."""
        return {
            "gemini_configured": self.is_gemini_configured,
            "google_cloud_project_set": bool(self.google_cloud_project),
            "parallel_configured": self.is_parallel_configured,
            "parallel_mode": "live" if self.is_parallel_configured else "not-configured",
            "model": self.gemini_model,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
