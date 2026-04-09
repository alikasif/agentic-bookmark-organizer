"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    openrouter_api_key: str
    backend_host: str = "127.0.0.1"
    backend_port: int = 8765
    fetch_concurrency: int = 10
    fetch_timeout_seconds: float = 5.0
    ai_batch_size: int = 50
    ai_base_url: str = "https://openrouter.ai/api/v1"
    ai_model: str = "openai/gpt-4o"
    cors_origins: list[str] = ["chrome-extension://*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
