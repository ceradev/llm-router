from __future__ import annotations

from packages.core.scoring.engine import ScoreBreakdown, compute_model_score
from packages.domain.gateway import (
    GatewayTask,
    HealthState,
    Intent,
    ModelTier,
    NoModelsAvailableError,
    Priority,
    RoutingDecision,
    ScoredCandidate,
)
from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.feedback_repository import FeedbackRepository
from packages.infrastructure.db.repositories.health_repository import HealthRepository
from packages.infrastructure.db.repositories.model_repository import (
    ModelRepository,
    ModelRoutingRow,
)
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.services.model_selection.snapshot_scoring import apply_snapshot_adjustments
from packages.services.prompt_evaluation.types import PromptEvaluationResult


def _pros_cons_for(*, model: ModelProfile, priority: Priority) -> tuple[tuple[str, ...], tuple[str, ...]]:
    pros: list[str] = []
    cons: list[str] = []
    if model.quality_score >= 4:
        pros.append("strong_quality_profile")
    elif model.quality_score <= 2:
        cons.append("limited_quality_profile")
    if model.latency_score >= 4:
        pros.append("low_latency_profile")
    if model.cost_score >= 4:
        pros.append("economical_profile")
    if priority == Priority.LOW_COST and model.cost_score < 3:
        cons.append("higher_cost_for_low_cost_priority")
    return (tuple(pros), tuple(cons))


class ModelSelector:
    def __init__(
        self,
        *,
        model_repository: ModelRepository,
        snapshot_repository: SnapshotRepository | None = None,
        health_repository: HealthRepository | None = None,
    ) -> None:
        self.model_repository = model_repository
        self.snapshot_repository = snapshot_repository
        self.health_repository = health_repository

    def build_decision(
        self,
        *,
        task: GatewayTask,
        intent: Intent,
        evaluation: PromptEvaluationResult,
        require_json: bool | None = None,
    ) -> RoutingDecision:
        effective_json = task.require_json if require_json is None else require_json
        db_rows_with_tiers, pref_applied, pref_fallback_used, normalized_pref = self._load_candidates(
            task=task,
            priority=task.priority,
            require_json=effective_json,
        )
        candidates, scored_candidates, score_breakdowns = self._rank_candidates(
            task=task,
            rows_with_tiers=db_rows_with_tiers,
            priority=task.priority,
            evaluation=evaluation,
        )

        if not candidates:
            raise NoModelsAvailableError("Model catalog not initialized")

        temperature = task.temperature
        if temperature is None:
            temperature = self._default_temperature(intent, candidates[0])

        reason = self._build_reason(
            intent=intent,
            priority=task.priority,
            primary_model=candidates[0].model_id,
            ranked=candidates,
            score_breakdowns=score_breakdowns,
        )

        return RoutingDecision(
            intent=intent,
            reason=reason,
            applied_temperature=temperature,
            candidates=candidates,
            scored_candidates=scored_candidates,
            preferred_providers=normalized_pref,
            preferred_providers_applied=pref_applied,
            preferred_providers_fallback_used=pref_fallback_used,
        )

    def _load_candidates(
        self,
        *,
        task: GatewayTask,
        priority: Priority,
        require_json: bool,
    ) -> tuple[list[tuple[ModelRoutingRow, ModelTier]], bool, bool, list[str]]:
        raw = task.preferred_providers
        normalized_pref = [str(p).strip().lower() for p in raw if str(p).strip()]

        def _split_and_filter(rows: list[ModelRoutingRow]) -> list[tuple[ModelRoutingRow, ModelTier]]:
            broken_ids = self.health_repository.get_broken_model_ids() if self.health_repository else set()
            available = [r for r in rows if r.db_model_id not in broken_ids]
            
            tier1 = [(r, ModelTier.TIER1_VERIFIED) for r in available if r.model.evaluation_status == "verified"]
            tier2 = [(r, ModelTier.TIER2_PROVISIONAL) for r in available if r.model.evaluation_status != "verified"]
            
            if not task.discovery_mode and tier1:
                return tier1
            return tier1 + tier2

        if not normalized_pref:
            rows = self.model_repository.list_routing_candidates(priority=priority, require_json=require_json)
            return (_split_and_filter(rows), False, False, [])

        filtered = self.model_repository.list_routing_candidates(
            priority=priority,
            require_json=require_json,
            provider_slugs=normalized_pref,
        )
        if filtered:
            return (_split_and_filter(filtered), True, False, normalized_pref)

        # Fallback behavior: if strict filter yields no candidates, use full catalog
        rows = self.model_repository.list_routing_candidates(priority=priority, require_json=require_json)
        return (_split_and_filter(rows), False, True, normalized_pref)

    def _rank_candidates(
        self,
        *,
        task: GatewayTask,
        rows_with_tiers: list[tuple[ModelRoutingRow, ModelTier]],
        priority: Priority,
        evaluation: PromptEvaluationResult,
    ) -> tuple[list[ModelProfile], tuple[ScoredCandidate, ...], dict[str, ScoreBreakdown]]:
        scored: list[tuple[float, ModelProfile, ModelRoutingRow, ModelTier, ScoreBreakdown, float | None]] = []
        model_ids = [row.db_model_id for row, _ in rows_with_tiers]
        feedback_stats: dict[int, tuple[float | None, int]] = {}
        session = getattr(self.model_repository, "session", None)
        if session is not None:
            feedback_stats = FeedbackRepository(session).get_feedback_stats_by_model_ids(model_ids=model_ids)
        
        for row, tier in rows_with_tiers:
            avg_rating, ratings_count = feedback_stats.get(row.db_model_id, (None, 0))
            
            # Apply snapshot adjustments if repository available
            snapshot = None
            if self.snapshot_repository:
                snapshot = self.snapshot_repository.get_latest_snapshot(model_id=row.db_model_id)
            
            adjustments = apply_snapshot_adjustments(profile=row.model, snapshot=snapshot)
            
            # Create adjusted profile for scoring
            adjusted_profile = ModelProfile(
                model_id=row.model.model_id,
                provider=row.model.provider,
                quality_score=row.model.quality_score,
                latency_score=int(adjustments.latency_score),
                cost_score=int(adjustments.cost_score),
                default_temperature=row.model.default_temperature,
                capabilities=row.model.capabilities,
                model_categories=row.model.model_categories,
                technical_capabilities=row.model.technical_capabilities,
                verification_scopes=row.model.verification_scopes,
                supports_tools=row.model.supports_tools,
                context_window=row.model.context_window,
                max_output_tokens=row.model.max_output_tokens,
                tier=row.model.tier,
                evaluation_status=row.model.evaluation_status,
                supports_vision=row.model.supports_vision,
                input_modalities=row.model.input_modalities,
                output_modalities=row.model.output_modalities,
                prompt_price=row.model.prompt_price,
                completion_price=row.model.completion_price,
            )

            breakdown = compute_model_score(
                model=adjusted_profile,
                priority=priority,
                priority_weight=row.priority_weight,
                complexity_score=evaluation.complexity_score,
                requires_code=evaluation.requires_code,
                requires_reasoning=evaluation.requires_reasoning,
                requires_tools=evaluation.requires_tools,
                use_cases=task.use_cases,
                preferred_providers=task.preferred_providers,
                avg_rating=avg_rating,
                ratings_count=ratings_count,
            )
            # Add reliability penalty if snapshot was used
            final_total = breakdown.total - adjustments.reliability_penalty
            
            scored.append((
                final_total, 
                row.model, 
                row, 
                tier, 
                breakdown, 
                snapshot.p50_latency_ms if snapshot else None
            ))

        scored.sort(key=lambda item: (-item[0], item[1].model_id))
        candidates = [model for _, model, _, _, _, _ in scored]
        score_breakdowns = {model.model_id: breakdown for _, model, _, _, breakdown, _ in scored}

        scored_candidates: list[ScoredCandidate] = []
        for rank, (total_score, model, row, tier, breakdown, p50) in enumerate(scored, start=1):
            avg_rating, ratings_count = feedback_stats.get(row.db_model_id, (None, 0))
            pros, cons = _pros_cons_for(model=model, priority=priority)
            
            health_status = HealthState.HEALTHY
            if self.health_repository:
                health_status = self.health_repository.get_status(model_id=row.db_model_id)

            scored_candidates.append(
                ScoredCandidate(
                    model=model,
                    priority_weight=row.priority_weight,
                    db_model_id=row.db_model_id,
                    rank=rank,
                    quality_score=float(model.quality_score),
                    latency_score=float(model.latency_score),
                    cost_score=float(model.cost_score),
                    final_score=total_score,
                    model_score_adjustment=breakdown.model_score_adjustment,
                    explanation=breakdown.explanation,
                    pros=pros,
                    cons=cons,
                    tier=tier,
                    health_status=health_status,
                    snapshot_latency_p50=p50,
                    user_rating=avg_rating,
                    user_rating_count=ratings_count,
                )
            )

        return candidates, tuple(scored_candidates), score_breakdowns

    def _default_temperature(self, intent: Intent, primary_model: ModelProfile) -> float:
        if intent == Intent.CODE:
            return 0.1
        if intent == Intent.CREATIVE:
            return 0.8
        if intent == Intent.ANALYSIS:
            return 0.2
        return primary_model.default_temperature

    def _build_reason(
        self,
        *,
        intent: Intent,
        priority: Priority,
        primary_model: str,
        ranked: list[ModelProfile],
        score_breakdowns: dict[str, ScoreBreakdown],
    ) -> str:
        short_name = primary_model.split("/")[-1].replace("-", " ").title()
        intent_label = {
            Intent.CODE: "coding",
            Intent.ANALYSIS: "analysis",
            Intent.CREATIVE: "creative",
            Intent.GENERAL: "general",
        }.get(intent, "general")
        priority_label = {
            Priority.HIGH_QUALITY: "best quality",
            Priority.LOW_LATENCY: "fast response",
            Priority.LOW_COST: "lower cost",
            Priority.BALANCED: "balanced quality and speed",
        }.get(priority, "balanced quality and speed")

        reason = (
            f"We picked {short_name} because it is a strong match for {intent_label} tasks "
            f"and your preference for {priority_label}."
        )
        if ranked and score_breakdowns.get(primary_model) is not None:
            reason += " It ranked highest among the currently available options."
        return reason
