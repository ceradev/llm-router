from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from app.providers.config.groq import PROVIDER_NAME


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="groq/gateway-low-latency",
            provider=PROVIDER_NAME,
            quality_score=2,
            latency_score=5,
            cost_score=4,
            default_temperature=0.3,
            capabilities={
                Capability.GENERAL,
                Capability.JSON,
            },
        )
    ]
