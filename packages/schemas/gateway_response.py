from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.gateway import Intent, Priority
from packages.domain.models import Capability


class InvocationAttemptResponse(BaseModel):
    provider: str
    model_id: str
    status: str
    detail: str
    latency_ms: int | None = None


class RankedModelResponse(BaseModel):
    model_id: str
    rank: int
    quality_score: float
    latency_score: float
    cost_score: float
    final_score: float
    model_score_adjustment: float = 0.0
    explanation: str
    pros: list[str] | None = None
    cons: list[str] | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_json: bool = False
    supports_tools: bool = False
    model_categories: list[str] = Field(default_factory=list)
    technical_capabilities: list[str] = Field(default_factory=list)
    verification_scopes: list[str] = Field(default_factory=list)
    # Legacy category field kept for compatibility with existing clients.
    capabilities: list[str] = Field(default_factory=list)
    is_free: bool = False
    tier: str = "alternative"
    evaluation_status: str = "cataloged"
    supports_vision: bool = False
    input_modalities: list[str] = Field(default_factory=list)
    output_modalities: list[str] = Field(default_factory=list)
    model_type_labels: list[str] = Field(default_factory=list)
    is_verified: bool = False
    public_status_key: str | None = None
    user_rating: float | None = None
    user_rating_count: int = 0
    cost_per_million_input: float | None = None
    cost_per_million_output: float | None = None


class RankingHighlightResponse(BaseModel):
    model_id: str
    display_name: str
    provider: str
    reason_key: str
    same_as_best_overall: bool = False


class RankingSummaryResponse(BaseModel):
    best_overall: RankingHighlightResponse
    free_alternative: RankingHighlightResponse | None
    best_quality: RankingHighlightResponse
    best_cost: RankingHighlightResponse
    best_speed: RankingHighlightResponse


class GatewayResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    request_id: UUID
    content: str
    provider: str
    model_id: str = Field(description="Model that produced content (after routing / fallback).")
    recommended_model_id: str = Field(
        description="Highest-ranked candidate before execution (may differ if fallback ran).",
    )
    response_latency_ms: int | None = Field(
        default=None,
        description="Measured latency for the successful provider call, when available.",
    )
    intent: Intent
    priority: Priority
    applied_temperature: float
    routing_reason: str
    explanation: str
    ranking_summary: RankingSummaryResponse
    ranking: list[RankedModelResponse]
    fallback_used: bool
    candidate_models: list[str]
    attempts: list[InvocationAttemptResponse]
    preferred_providers: list[str] = Field(default_factory=list)
    preferred_providers_applied: bool = False
    preferred_providers_fallback_used: bool = False


class ModelSummaryResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_id: str
    provider: str
    quality_score: int
    latency_score: int
    cost_score: int
    supports_json: bool
    model_categories: list[str] = Field(default_factory=list)
    technical_capabilities: list[str] = Field(default_factory=list)
    verification_scopes: list[str] = Field(default_factory=list)
    capabilities: list[Capability]
