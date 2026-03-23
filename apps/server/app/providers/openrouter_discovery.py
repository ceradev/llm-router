from __future__ import annotations

from collections.abc import Iterable

import httpx

from app.core.settings import get_settings
from app.providers.base import DiscoveredProviderModel, ProviderDiscoveryError
from app.providers.config.openrouter import PROVIDER_NAME


class OpenRouterModelDiscoveryClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openrouter_api_key
        self.base_url = (base_url if base_url is not None else settings.openrouter_base_url).rstrip("/")
        self.timeout = timeout
        self._client = client

    def list_models(self) -> list[DiscoveredProviderModel]:
        if not self.api_key:
            raise ProviderDiscoveryError("OPENROUTER_API_KEY is required for model discovery")

        response = self._request_models()
        payload = self._parse_payload(response)
        return [self._parse_model(item) for item in payload]

    def _request_models(self) -> httpx.Response:
        try:
            if self._client is not None:
                response = self._client.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                )
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(
                        f"{self.base_url}/models",
                        headers=self._headers(),
                    )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise ProviderDiscoveryError(
                f"OpenRouter model discovery failed with status {status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderDiscoveryError("OpenRouter model discovery request failed") from exc
        return response

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def _parse_payload(self, response: httpx.Response) -> Iterable[object]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderDiscoveryError("OpenRouter model discovery returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise ProviderDiscoveryError("OpenRouter model discovery payload is not an object")

        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderDiscoveryError("OpenRouter model discovery payload missing 'data' list")
        return data

    def _parse_model(self, item: object) -> DiscoveredProviderModel:
        if not isinstance(item, dict):
            raise ProviderDiscoveryError("OpenRouter model discovery payload contains a non-object item")

        external_model_id = item.get("id")
        if not isinstance(external_model_id, str) or not external_model_id:
            raise ProviderDiscoveryError("OpenRouter model discovery payload item missing valid 'id'")

        canonical_slug = item.get("canonical_slug")
        if canonical_slug is not None and not isinstance(canonical_slug, str):
            raise ProviderDiscoveryError(
                "OpenRouter model discovery payload item has invalid 'canonical_slug'"
            )

        created_at_unix = item.get("created")
        if created_at_unix is not None and not isinstance(created_at_unix, int):
            raise ProviderDiscoveryError("OpenRouter model discovery payload item has invalid 'created'")

        return DiscoveredProviderModel(
            provider=PROVIDER_NAME,
            external_model_id=external_model_id,
            owned_by=canonical_slug,
            created_at_unix=created_at_unix,
        )
