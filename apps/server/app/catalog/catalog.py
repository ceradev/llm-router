from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from app.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from app.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from app.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from app.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="openai/gateway-fast",
            provider=OPENAI_PROVIDER,
            quality_score=3,
            latency_score=4,
            cost_score=3,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        ),
        ModelProfile(
            model_id="anthropic/gateway-quality",
            provider=ANTHROPIC_PROVIDER,
            quality_score=5,
            latency_score=2,
            cost_score=1,
            default_temperature=0.2,
            capabilities={
                Capability.GENERAL,
                Capability.ANALYSIS,
            },
        ),
        ModelProfile(
            model_id="groq/gateway-low-latency",
            provider=GROQ_PROVIDER,
            quality_score=2,
            latency_score=5,
            cost_score=4,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        ),
        ModelProfile(
            model_id="deepseek/gateway-code",
            provider=DEEPSEEK_PROVIDER,
            quality_score=4,
            latency_score=3,
            cost_score=4,
            default_temperature=0.1,
            capabilities={
                Capability.CODE,
                Capability.JSON,
            },
        ),
    ]
