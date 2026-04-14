from __future__ import annotations

from typing import Any

from packages.infrastructure.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from packages.infrastructure.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from packages.infrastructure.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from packages.infrastructure.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER
from packages.infrastructure.providers.config.openrouter import PROVIDER_NAME as OPENROUTER_PROVIDER
from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.infrastructure.providers.http_provider_client import HttpProviderClient
from packages.infrastructure.providers.base import ProviderAdapter


def build_provider_clients(settings: Any) -> dict[str, ProviderAdapter]:
    def get_client(provider: str, api_key: str | None) -> ProviderAdapter:
        if api_key:
            return HttpProviderClient(provider, api_key)
        return DemoProviderClient(provider)

    return {
        OPENAI_PROVIDER: get_client(OPENAI_PROVIDER, getattr(settings, "openai_api_key", None)),
        ANTHROPIC_PROVIDER: get_client(ANTHROPIC_PROVIDER, getattr(settings, "anthropic_api_key", None)),
        GROQ_PROVIDER: get_client(GROQ_PROVIDER, getattr(settings, "groq_api_key", None)),
        DEEPSEEK_PROVIDER: get_client(DEEPSEEK_PROVIDER, getattr(settings, "deepseek_api_key", None)),
        OPENROUTER_PROVIDER: get_client(OPENROUTER_PROVIDER, getattr(settings, "openrouter_api_key", None)),
    }

