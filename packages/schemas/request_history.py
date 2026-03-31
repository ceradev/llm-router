from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestListItem(BaseModel):
    id: UUID
    prompt: str
    intent: str
    priority: str
    selected_model: str | None
    fallback_used: bool
    created_at: datetime


class RequestListResponse(BaseModel):
    items: list[RequestListItem]
    total: int
    limit: int
    offset: int


class AttemptDetail(BaseModel):
    provider_slug: str
    model_routing_key: str
    attempt_order: int
    status: str
    error: str | None
    latency_ms: int | None


class ModelEvaluationDetail(BaseModel):
    model_id: int
    quality_score: int
    latency_score: int
    cost_score: int
    final_score: float
    evaluation_rank: int
    explanation: str | None
    pros: list[str] | None
    cons: list[str] | None


class RequestAnalysisDetail(BaseModel):
    id: UUID
    task_type: str
    complexity_score: float
    cost_sensitivity: float
    latency_sensitivity: float
    detected_skills: list[str] | None
    tokens_estimated: int
    created_at: datetime


class ExecutionDetail(BaseModel):
    id: UUID
    model_id: int
    model_routing_key: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost: float
    success: bool
    error: str | None
    created_at: datetime


class FeedbackDetail(BaseModel):
    id: UUID
    request_id: UUID | None
    model_id: int
    rating: int
    comment: str | None
    created_at: datetime


class RequestDetailResponse(BaseModel):
    id: UUID
    prompt: str
    intent: str
    priority: str
    require_json: bool
    fallback_used: bool
    created_at: datetime
    selected_model: str | None
    analysis: RequestAnalysisDetail | None
    evaluations: list[ModelEvaluationDetail]
    execution: ExecutionDetail | None
    attempts: list[AttemptDetail]
    feedback: FeedbackDetail | None


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ModelFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    request_id: UUID | None = None
