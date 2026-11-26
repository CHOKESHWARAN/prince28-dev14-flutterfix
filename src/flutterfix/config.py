"""All settings come from environment variables (or a local .env file)."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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

    # LLM gateway. Keys stay empty in CI and are supplied via environment in production.
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_primary_model: str = "gemini-3.8-flash"
    llm_fallback_model: str = "openai/gpt-oss-20b"
    llm_primary_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_fallback_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 30.0
    usd_inr: float = 95.0
    prompts_dir: Path = Path("prompts")

    def model_post_init(self, __context: object) -> None:
        # Render Git deploys do not pass the Docker build argument.
        if self.git_sha in {"", "dev", "local"}:
            self.git_sha = os.getenv("RENDER_GIT_COMMIT") or self.git_sha or "dev"

    def validate_database_config(self) -> None:
        if self.app_env == "production" and self.database_url is None:
            raise ValueError("DATABASE_URL is required in production.")


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    settings = Settings()
    settings.validate_database_config()
    return settings
