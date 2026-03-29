from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenRouterClientError(RuntimeError):
    """Raised when the OpenRouter models API cannot be fetched or parsed."""


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        http_referer: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._base = (base_url or self.BASE_URL).rstrip("/")
        self._timeout = timeout_seconds
        self._http_referer = http_referer
        raw = (api_key or "").strip()
        self._api_key = raw or None

    def fetch_models(self) -> list[dict[str, Any]]:
        url = f"{self._base}/models"
        headers: dict[str, str] = {"User-Agent": "llm-router/1.0 (OpenRouter sync)"}
        if self._http_referer:
            headers["Referer"] = self._http_referer
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.error("OpenRouter HTTP error: %s", exc)
            raise OpenRouterClientError(f"OpenRouter request failed: {exc}") from exc
        except ValueError as exc:
            logger.error("OpenRouter invalid JSON: %s", exc)
            raise OpenRouterClientError("OpenRouter returned invalid JSON") from exc

        data = payload.get("data")
        if not isinstance(data, list):
            logger.error("OpenRouter payload missing data array")
            raise OpenRouterClientError("OpenRouter response missing data array")

        out: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        return out
