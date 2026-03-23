from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "LLM Gateway"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/llm_router"
    database_echo: bool = False
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
