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
    admin_api_key: str | None = None

    catalog_evaluation_after_openrouter_sync: bool = False
    catalog_evaluation_on_startup: bool = False
    catalog_evaluation_enable_periodic: bool = False
    catalog_evaluation_interval_hours: float = 24.0
    catalog_evaluation_max_models_per_run: int = 50
    catalog_evaluation_max_live_per_run: int = 10
    catalog_evaluation_provider_allowlist: str | None = None
    catalog_evaluation_include_verified_live: bool = False
    catalog_evaluation_live_delay_seconds: float = 2.0
    catalog_evaluation_enable_image_text_v2: bool = False
    catalog_evaluation_strict_image_text_checks: bool = True
    catalog_evaluation_enable_file_text_v3: bool = False
    catalog_evaluation_strict_file_text_checks: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

