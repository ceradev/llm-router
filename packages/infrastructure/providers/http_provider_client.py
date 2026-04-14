from __future__ import annotations

import httpx

from packages.domain.gateway import RoutedRequest
from packages.domain.models import ModelProfile
from packages.infrastructure.providers.base import ProviderAdapter, ProviderError, ProviderResponse


_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

_PROVIDER_AUTH_HEADERS: dict[str, str] = {
    "anthropic": "x-api-key",
}

class HttpProviderClient(ProviderAdapter):
    def __init__(self, provider: str, api_key: str, *, timeout_s: float = 30.0) -> None:
        self.provider = provider
        self.name = provider
        self._api_key = api_key
        self._base_url = _PROVIDER_BASE_URLS.get(provider, "https://openrouter.ai/api/v1")
        self._timeout = timeout_s
        auth_header = _PROVIDER_AUTH_HEADERS.get(provider, "Authorization")
        auth_value = api_key if provider == "anthropic" else f"Bearer {api_key}"
        self._headers = {
            auth_header: auth_value,
            "Content-Type": "application/json",
        }

    def generate(self, request: RoutedRequest, model: ModelProfile) -> ProviderResponse:
        import time
        payload = {
            "model": model.model_id.split("/", 1)[-1] if "/" in model.model_id else model.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.require_json:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        try:
            with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=self._timeout) as client:
                resp = client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"{self.provider} HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"{self.provider} network error: {exc}") from exc

        dt = int((time.perf_counter() - t0) * 1000)
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        i_tok = usage.get("prompt_tokens", 0)
        o_tok = usage.get("completion_tokens", 0)

        # Naive cost calculation
        cost_in = (i_tok / 1000.0) * 0.001
        cost_out = (o_tok / 1000.0) * 0.002

        return ProviderResponse(
            content=content,
            provider=self.provider,
            model_id=model.model_id,
            latency_ms=dt,
            input_tokens=i_tok,
            output_tokens=o_tok,
            cost=cost_in + cost_out,
        )
