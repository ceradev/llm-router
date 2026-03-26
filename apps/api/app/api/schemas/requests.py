from __future__ import annotations

from pydantic import BaseModel, Field

from app.gateway.types import Priority


class GatewayRequest(BaseModel):
    prompt: str = Field(min_length=1, description="User prompt to route")
    priority: Priority = Field(default=Priority.BALANCED)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=512, ge=1, le=8192)
    require_json: bool = False
    simulate_failures: list[str] = Field(
        default_factory=list,
        description="Providers or model ids to fail on purpose in demo mode.",
    )
