from __future__ import annotations

from app.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from app.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from app.providers.demo_client import DemoProviderClient
from app.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from app.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER


def build_provider_clients() -> dict[str, DemoProviderClient]:
    return {
        OPENAI_PROVIDER: DemoProviderClient(OPENAI_PROVIDER),
        ANTHROPIC_PROVIDER: DemoProviderClient(ANTHROPIC_PROVIDER),
        GROQ_PROVIDER: DemoProviderClient(GROQ_PROVIDER),
        DEEPSEEK_PROVIDER: DemoProviderClient(DEEPSEEK_PROVIDER),
    }
