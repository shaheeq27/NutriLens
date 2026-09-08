"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    gemini_api_key: str = ""
    backend_port: int = 8000
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_image_size_mb: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
