from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from packages.domain.gateway import GatewayTask, Priority

ResponseDepth = Literal["short", "balanced", "detailed"]


class GatewaySimpleRequest(BaseModel):
    """Prompt only; the gateway applies default routing options."""

    prompt: str = Field(min_length=1, description="User prompt to route with default options")


def build_default_gateway_task(*, prompt: str) -> GatewayTask:
    """Defaults for the simple completion endpoint (balanced, no JSON, demo off)."""
    return GatewayTask(
        prompt=prompt,
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=512,
        require_json=False,
        simulate_failures=[],
        use_cases=[],
        preferred_providers=[],
        response_depth="balanced",
    )


class GatewayRequest(BaseModel):
    """Full request including priority, sampling, and demo hooks (advanced)."""

    prompt: str = Field(min_length=1, description="User prompt to route")
    priority: Priority = Field(default=Priority.BALANCED)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=8192,
        description="Max output tokens; omit to derive from response_depth.",
    )
    require_json: bool = False
    simulate_failures: list[str] = Field(
        default_factory=list,
        description="Providers or model ids to fail on purpose in demo mode.",
    )
    use_cases: list[str] = Field(
        default_factory=list,
        description="Use cases: ide, api, chatbot, batch",
    )
    preferred_providers: list[str] = Field(
        default_factory=list,
        description="Preferred provider slugs",
    )
    response_depth: ResponseDepth = Field(
        default="balanced",
        description="short, balanced, or detailed (used for default max_tokens)",
    )
