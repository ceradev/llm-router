from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenRouterClientError(RuntimeError):
    """Raised when the OpenRouter API cannot be used or parsed."""


@dataclass(frozen=True)
class ChatCompletionResult:
    """Normalized OpenAI-compatible chat completion response."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    raw: dict[str, Any]
    tool_calls: list[dict[str, Any]] | None = None


class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 120.0,
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

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 256,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | object | None = None,
    ) -> ChatCompletionResult:
        """POST /chat/completions (OpenAI-compatible). Requires API key for real models."""

        if not self._api_key:
            raise OpenRouterClientError("OpenRouter API key is required for chat completions")

        url = f"{self._base}/chat/completions"
        headers: dict[str, str] = {
            "User-Agent": "llm-router/1.0 (benchmark)",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._http_referer:
            headers["HTTP-Referer"] = self._http_referer

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format is not None:
            body["response_format"] = response_format
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice

        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.error("OpenRouter chat HTTP error: %s", exc)
            raise OpenRouterClientError(f"OpenRouter chat completion failed: {exc}") from exc
        except ValueError as exc:
            raise OpenRouterClientError("OpenRouter chat returned invalid JSON") from exc

        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenRouterClientError("OpenRouter chat missing choices")

        first = choices[0]
        if not isinstance(first, dict):
            raise OpenRouterClientError("OpenRouter chat invalid choice")

        msg = first.get("message")
        if not isinstance(msg, dict):
            raise OpenRouterClientError("OpenRouter chat missing message")

        content = msg.get("content")
        content_str = content if isinstance(content, str) else ("" if content is None else str(content))

        tool_calls_raw = msg.get("tool_calls")
        tool_calls: list[dict[str, Any]] | None = None
        if isinstance(tool_calls_raw, list) and tool_calls_raw:
            tool_calls = [x for x in tool_calls_raw if isinstance(x, dict)]

        usage = payload.get("usage")
        input_tokens = 0
        output_tokens = 0
        if isinstance(usage, dict):
            input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)

        model_out = str(payload.get("model") or model)

        return ChatCompletionResult(
            content=content_str,
            model=model_out,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=elapsed_ms,
            raw=payload,
            tool_calls=tool_calls,
        )
