from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from packages.infrastructure.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from packages.infrastructure.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from packages.infrastructure.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from packages.infrastructure.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="openai/gateway-fast",
            provider=OPENAI_PROVIDER,
            quality_score=6,
            latency_score=8,
            cost_score=6,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        ),
        ModelProfile(
            model_id="anthropic/gateway-quality",
            provider=ANTHROPIC_PROVIDER,
            quality_score=10,
            latency_score=4,
            cost_score=2,
            default_temperature=0.2,
            capabilities={
                Capability.GENERAL,
                Capability.ANALYSIS,
            },
        ),
        ModelProfile(
            model_id="groq/gateway-low-latency",
            provider=GROQ_PROVIDER,
            quality_score=4,
            latency_score=10,
            cost_score=8,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        ),
        ModelProfile(
            model_id="deepseek/gateway-code",
            provider=DEEPSEEK_PROVIDER,
            quality_score=8,
            latency_score=6,
            cost_score=8,
            default_temperature=0.1,
            capabilities={
                Capability.CODE,
                Capability.JSON,
            },
        ),
    ]
