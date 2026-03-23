from __future__ import annotations

from app.catalog.types import ModelProfile
from app.gateway.types import ProviderResponse, RoutedRequest
from app.providers.anthropic.config import PROVIDER_NAME
from app.providers.anthropic.mapper import to_provider_response_content
from app.providers.base import ProviderError


class AnthropicClient:
    name = PROVIDER_NAME

    def generate(
        self,
        request: RoutedRequest,
        model: ModelProfile,
    ) -> ProviderResponse:
        failure_keys = {self.name, model.model_id}
        if request.simulate_failures & failure_keys:
            raise ProviderError(f"Simulated upstream failure for {model.model_id}")

        return ProviderResponse(
            content=to_provider_response_content(request, model, self.name),
            provider=self.name,
            model_id=model.model_id,
        )
