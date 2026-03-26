from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from packages.domain.gateway import Intent, Priority
from packages.domain.models import Capability


class InvocationAttemptResponse(BaseModel):
    provider: str
    model_id: str
    status: str
    detail: str


class GatewayResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    content: str
    provider: str
    model_id: str
    intent: Intent
    priority: Priority
    applied_temperature: float
    routing_reason: str
    fallback_used: bool
    candidate_models: list[str]
    attempts: list[InvocationAttemptResponse]


class ModelSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_id: str
    provider: str
    quality_score: int
    latency_score: int
    cost_score: int
    supports_json: bool
    capabilities: list[Capability]

