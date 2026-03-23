from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from app.providers.anthropic.config import PROVIDER_NAME


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="anthropic/gateway-quality",
            provider=PROVIDER_NAME,
            quality_score=5,
            latency_score=2,
            cost_score=1,
            default_temperature=0.2,
            capabilities={
                Capability.GENERAL,
                Capability.ANALYSIS,
            },
        )
    ]
