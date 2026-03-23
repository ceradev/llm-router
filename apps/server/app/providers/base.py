from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from app.catalog.types import Capability, ModelProfile
from app.gateway.types import ProviderResponse, RoutedRequest


class ProviderError(RuntimeError):
    """Raised when an upstream provider invocation fails."""


class ProviderDiscoveryError(RuntimeError):
    """Raised when model discovery against a provider fails."""


class ProviderAdapter(Protocol):
    name: str

    def generate(
        self,
        request: RoutedRequest,
        model: ModelProfile,
    ) -> ProviderResponse:
        """Execute a request against a concrete provider/model."""


@dataclass(frozen=True)
class DiscoveredProviderModel:
    provider: str
    external_model_id: str
    owned_by: str | None
    created_at_unix: int | None


def build_demo_content(request: RoutedRequest, model: ModelProfile, provider_name: str) -> str:
    prompt_preview = " ".join(request.prompt.split())[:160]
    if request.require_json and Capability.JSON in model.capabilities:
        return json.dumps(
            {
                "provider": provider_name,
                "model": model.model_id,
                "prompt_preview": prompt_preview,
                "note": "demo-response",
            }
        )
    return (
        f"[demo-response] provider={provider_name} model={model.model_id} "
        f"temperature={request.temperature:.1f} prompt='{prompt_preview}'"
    )
