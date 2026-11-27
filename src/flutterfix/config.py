"""All settings come from environment variables (or a local .env file)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "flutterfix"

    # No default on purpose: if APP_ENV is missing, the app refuses to start.
    app_env: Literal["local", "ci", "production"]

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_file: Path = Path("data/sample_records.json")

    # Neon PostgreSQL connection
    database_url: SecretStr | None = None

    # Embedded commit SHA / release version
    git_sha: str = "dev"
    render_git_commit: str | None = None

    # LLM gateway (Day 8). Keys default to empty so tests and CI never need them.
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_primary_model: str = "gemini-3.8-flash"
    llm_fallback_model: str = "openai/gpt-oss-20b"
    # Both providers speak the OpenAI API, so any compatible server works (Ollama, a test fake).
    llm_primary_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_fallback_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 30.0
    usd_inr: float = 95.0  # rupees per US dollar, for cost estimates
    prompts_dir: Path = Path("prompts")

    # Queue & Background Ingestion (Day 10)
    redis_url: str = "redis://localhost:6379/0"
    manifest_file: Path = Path("data/manifest.jsonl")
    admin_token: SecretStr = SecretStr("dev-admin-secret-token")
    worker_in_api: bool = False
    ingest_concurrency: int = 2
    ingest_rpm: float = 12.0
    ingest_job_timeout: int = 60
    ingest_max_tries: int = 3

    @model_validator(mode="after")
    def resolve_git_sha(self) -> "Settings":
        if self.render_git_commit and (not self.git_sha or self.git_sha in {"dev", "local"}):
            self.git_sha = self.render_git_commit
        return self

    def validate_database_config(self) -> None:
        if self.app_env == "production" and self.database_url is None:
            raise ValueError("DATABASE_URL is required in production.")


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    settings = Settings()
    settings.validate_database_config()
    return settings
