"""
Application configuration, loaded from environment variables.

Variable names here are a contract with .env.example at the repo root —
do not rename one without updating the other. See .env.example for what
each variable does.

Path in repo: backend/app/core/config.py
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_vision_model: str = "google/gemma-4-31b-it:free"
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "production", "test"] = Field(
        default="development", alias="ENVIRONMENT"
    )

    # When true, every provider (vision, OCR, nutrition lookup) returns a
    # canned response instead of calling a real external API. See
    # README: "Providers are mocked first; real external APIs are wired
    # in only after the mocked path is tested."
    use_mock_providers: bool = Field(default=True, alias="USE_MOCK_PROVIDERS")

    # Comma-separated list of origins allowed to call the backend API.
    cors_allowed_origins: str = Field(
        default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS"
    )

    # Cloud Run injects PORT automatically in production; this default is
    # only used for local development.
    port: int = Field(default=8080, alias="PORT")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """CORS middleware wants a list, not a raw comma-separated string."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so env vars are read once per process, not on every request.
    Use `get_settings.cache_clear()` in tests that need to reload env vars."""
    return Settings()
