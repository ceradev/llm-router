from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from app.providers.config.openai import PROVIDER_NAME


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="openai/gateway-fast",
            provider=PROVIDER_NAME,
            quality_score=3,
            latency_score=4,
            cost_score=3,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        )
    ]
