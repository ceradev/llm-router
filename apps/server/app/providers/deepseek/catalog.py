from __future__ import annotations

from app.catalog.types import Capability, ModelProfile
from app.providers.config.deepseek import PROVIDER_NAME


def list_models() -> list[ModelProfile]:
    return [
        ModelProfile(
            model_id="deepseek/gateway-code",
            provider=PROVIDER_NAME,
            quality_score=4,
            latency_score=3,
            cost_score=4,
            default_temperature=0.1,
            capabilities={
                Capability.CODE,
                Capability.JSON,
            },
        )
    ]
