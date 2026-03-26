from __future__ import annotations

from packages.infrastructure.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from packages.infrastructure.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from packages.infrastructure.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from packages.infrastructure.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER
from packages.infrastructure.providers.demo_provider import DemoProviderClient


def build_provider_clients() -> dict[str, DemoProviderClient]:
    return {
        OPENAI_PROVIDER: DemoProviderClient(OPENAI_PROVIDER),
        ANTHROPIC_PROVIDER: DemoProviderClient(ANTHROPIC_PROVIDER),
        GROQ_PROVIDER: DemoProviderClient(GROQ_PROVIDER),
        DEEPSEEK_PROVIDER: DemoProviderClient(DEEPSEEK_PROVIDER),
    }

