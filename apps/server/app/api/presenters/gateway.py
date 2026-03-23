from __future__ import annotations

from app.api.schemas.responses import (
    GatewayResponse,
    InvocationAttemptResponse,
    ModelSummaryResponse,
)
from app.catalog.types import ModelProfile
from app.gateway.types import GatewayExecutionResult, InvocationAttempt, Priority


def to_attempt_response(attempt: InvocationAttempt) -> InvocationAttemptResponse:
    return InvocationAttemptResponse(
        provider=attempt.provider,
        model_id=attempt.model_id,
        status=attempt.status,
        detail=attempt.detail,
    )


def to_gateway_response(
    result: GatewayExecutionResult,
    *,
    priority: Priority,
) -> GatewayResponse:
    return GatewayResponse(
        content=result.response.content,
        provider=result.response.provider,
        model_id=result.response.model_id,
        intent=result.decision.intent,
        priority=priority,
        applied_temperature=result.decision.applied_temperature,
        routing_reason=result.decision.reason,
        fallback_used=len(result.attempts) > 1,
        candidate_models=[model.model_id for model in result.decision.candidates],
        attempts=[to_attempt_response(attempt) for attempt in result.attempts],
    )


def to_model_summary_list(models: list[ModelProfile]) -> list[ModelSummaryResponse]:
    return [
        ModelSummaryResponse(
            model_id=model.model_id,
            provider=model.provider,
            quality_score=model.quality_score,
            latency_score=model.latency_score,
            cost_score=model.cost_score,
            supports_json=model.supports_json,
            capabilities=sorted(model.capabilities, key=lambda item: item.value),
        )
        for model in models
    ]
