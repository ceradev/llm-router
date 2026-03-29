from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM Gateway"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/llm_router"
    database_echo: bool = False

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    openrouter_fetch_timeout_seconds: float = 30.0
    openrouter_http_referer: str | None = None
    openrouter_auto_sync_on_empty_catalog: bool = False
    seed_models_on_startup: bool = False
    openrouter_sync_on_startup: bool = False
    openrouter_enable_periodic_sync: bool = False
    openrouter_sync_interval_hours: float = 6.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

