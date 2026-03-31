from __future__ import annotations

from packages.domain.gateway import (
    GatewayExecutionResult,
    Intent,
    InvocationAttempt,
    Priority,
    RankingHighlight,
    RankingSummary,
    ScoredCandidate,
)
from packages.domain.models import ModelProfile
from packages.schemas.gateway_response import (
    GatewayResponse,
    InvocationAttemptResponse,
    ModelSummaryResponse,
    RankedModelResponse,
    RankingHighlightResponse,
    RankingSummaryResponse,
)
from packages.schemas.ranking_public_fields import (
    compute_model_categories,
    compute_model_type_labels,
    compute_technical_capabilities,
    compute_verification_scopes,
    public_status_fields,
)


def _to_cost_per_million(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1_000_000


def to_attempt_response(attempt: InvocationAttempt) -> InvocationAttemptResponse:
    return InvocationAttemptResponse(
        provider=attempt.provider,
        model_id=attempt.model_id,
        status=attempt.status,
        detail=attempt.detail,
        latency_ms=attempt.latency_ms,
    )


def scored_candidate_to_ranked_response(candidate: ScoredCandidate) -> RankedModelResponse:
    caps = sorted({c.value for c in candidate.model.capabilities})
    tier = candidate.model.tier
    ev = candidate.model.evaluation_status
    verified_flag, public_status_key = public_status_fields(ev)
    return RankedModelResponse(
        model_id=candidate.model.model_id,
        rank=candidate.rank,
        quality_score=candidate.quality_score,
        latency_score=candidate.latency_score,
        cost_score=candidate.cost_score,
        final_score=candidate.final_score,
        model_score_adjustment=candidate.model_score_adjustment,
        explanation=candidate.explanation,
        pros=list(candidate.pros) if candidate.pros else None,
        cons=list(candidate.cons) if candidate.cons else None,
        context_window=candidate.model.context_window,
        max_output_tokens=candidate.model.max_output_tokens,
        supports_json=candidate.model.supports_json,
        supports_tools=candidate.model.supports_tools,
        model_categories=compute_model_categories(candidate.model),
        technical_capabilities=compute_technical_capabilities(candidate.model),
        verification_scopes=compute_verification_scopes(candidate.model),
        capabilities=caps,
        is_free=tier == "free",
        tier=tier,
        evaluation_status=ev,
        supports_vision=candidate.model.supports_vision,
        input_modalities=list(candidate.model.input_modalities),
        output_modalities=list(candidate.model.output_modalities),
        model_type_labels=compute_model_type_labels(candidate.model),
        is_verified=verified_flag,
        public_status_key=public_status_key,
        user_rating=candidate.user_rating,
        user_rating_count=candidate.user_rating_count,
        cost_per_million_input=_to_cost_per_million(candidate.model.prompt_price),
        cost_per_million_output=_to_cost_per_million(candidate.model.completion_price),
    )


def ranking_highlight_to_response(highlight: RankingHighlight) -> RankingHighlightResponse:
    return RankingHighlightResponse(
        model_id=highlight.model_id,
        display_name=highlight.display_name,
        provider=highlight.provider,
        reason_key=highlight.reason_key,
        same_as_best_overall=highlight.same_as_best_overall,
    )


def ranking_summary_to_response(summary: RankingSummary) -> RankingSummaryResponse:
    return RankingSummaryResponse(
        best_overall=ranking_highlight_to_response(summary.best_overall),
        free_alternative=(
            ranking_highlight_to_response(summary.free_alternative)
            if summary.free_alternative is not None
            else None
        ),
        best_quality=ranking_highlight_to_response(summary.best_quality),
        best_cost=ranking_highlight_to_response(summary.best_cost),
        best_speed=ranking_highlight_to_response(summary.best_speed),
    )


def _gateway_explanation(*, routing_reason: str, intent: Intent, priority: Priority) -> str:
    return routing_reason


def to_gateway_response(
    result: GatewayExecutionResult,
    *,
    priority: Priority,
) -> GatewayResponse:
    ranking = [scored_candidate_to_ranked_response(c) for c in result.decision.scored_candidates]
    recommended_id = (
        result.decision.candidates[0].model_id if result.decision.candidates else result.response.model_id
    )
    return GatewayResponse(
        request_id=result.request_id,
        content=result.response.content,
        provider=result.response.provider,
        model_id=result.response.model_id,
        recommended_model_id=recommended_id,
        response_latency_ms=result.response.latency_ms,
        intent=result.decision.intent,
        priority=priority,
        applied_temperature=result.decision.applied_temperature,
        routing_reason=result.decision.reason,
        explanation=_gateway_explanation(
            routing_reason=result.decision.reason,
            intent=result.decision.intent,
            priority=priority,
        ),
        ranking_summary=ranking_summary_to_response(result.ranking_summary),
        ranking=ranking,
        fallback_used=result.fallback_used,
        candidate_models=[model.model_id for model in result.decision.candidates],
        attempts=[to_attempt_response(attempt) for attempt in result.attempts],
        preferred_providers=list(result.decision.preferred_providers),
        preferred_providers_applied=result.decision.preferred_providers_applied,
        preferred_providers_fallback_used=result.decision.preferred_providers_fallback_used,
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
            model_categories=compute_model_categories(model),
            technical_capabilities=compute_technical_capabilities(model),
            verification_scopes=compute_verification_scopes(model),
            capabilities=sorted(model.capabilities, key=lambda item: item.value),
        )
        for model in models
    ]
