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
