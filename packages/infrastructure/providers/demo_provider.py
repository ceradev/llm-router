from __future__ import annotations

from packages.domain.models import ModelProfile
from packages.domain.gateway import ProviderResponse, RoutedRequest
from packages.infrastructure.providers.base import ProviderError, build_demo_content


class DemoProviderClient:
    def __init__(self, provider_name: str) -> None:
        self.name = provider_name

    def generate(
        self,
        request: RoutedRequest,
        model: ModelProfile,
    ) -> ProviderResponse:
        failure_keys = {self.name, model.model_id}
        if request.simulate_failures & failure_keys:
            raise ProviderError(f"Simulated upstream failure for {model.model_id}")

        return ProviderResponse(
            content=build_demo_content(request, model, self.name),
            provider=self.name,
            model_id=model.model_id,
        )

