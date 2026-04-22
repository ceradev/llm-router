from __future__ import annotations

import math

from packages.core.scoring.engine import ScoreBreakdown, apply_gap_decision, compute_model_score
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
from packages.services.prompt_evaluation.types import PromptEvaluationResult
from packages.services.real_time_observer import RealTimeObserver


def _pros_cons_for(*, model: ModelProfile, priority: Priority) -> tuple[tuple[str, ...], tuple[str, ...]]:
    pros: list[str] = []
    cons: list[str] = []
    if model.quality_score >= 8:
        pros.append("strong_quality_profile")
    elif model.quality_score <= 3:
        cons.append("limited_quality_profile")
    if model.latency_score >= 8:
        pros.append("low_latency_profile")
    if model.cost_score >= 8:
        pros.append("economical_profile")
    if priority == Priority.LOW_COST and model.cost_score < 6:
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
            intent=intent,
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
        intent: Intent,
        evaluation: PromptEvaluationResult,
    ) -> tuple[list[ModelProfile], tuple[ScoredCandidate, ...], dict[str, ScoreBreakdown]]:
        scored: list[
            tuple[
                float,
                ModelProfile,
                ModelRoutingRow,
                ModelTier,
                ScoreBreakdown,
                float | None,
                float | None,
            ]
        ] = []
        model_ids = [row.db_model_id for row, _ in rows_with_tiers]
        feedback_stats: dict[int, tuple[float | None, int]] = {}
        session = getattr(self.model_repository, "session", None)
        if session is not None:
            feedback_stats = FeedbackRepository(session).get_feedback_stats_by_model_ids(model_ids=model_ids)

        routing_keys = [row.model.model_id for row, _ in rows_with_tiers]
        realtime_snapshot = None
        if session is not None:
            realtime_snapshot = RealTimeObserver(session).get_health_snapshot(routing_keys=routing_keys)
        total_attempts = (
            sum(signal.attempt_count for signal in realtime_snapshot.signals.values())
            if realtime_snapshot is not None
            else 0
        )

        for row, tier in rows_with_tiers:
            avg_rating, ratings_count = feedback_stats.get(row.db_model_id, (None, 0))

            snapshot = None
            if self.snapshot_repository:
                snapshot = self.snapshot_repository.get_latest_snapshot(model_id=row.db_model_id)

            signal = realtime_snapshot.signals.get(row.model.model_id) if realtime_snapshot else None
            observed_latency_ms = snapshot.p50_latency_ms if snapshot and snapshot.p50_latency_ms is not None else None
            observed_cost_per_1k = (
                snapshot.avg_cost_per_1k_tokens
                if snapshot and snapshot.avg_cost_per_1k_tokens is not None
                else None
            )
            failure_rate = signal.failure_rate if signal else 0.0
            avg_latency_ms = signal.avg_latency_ms if signal and signal.avg_latency_ms is not None else observed_latency_ms
            health_multiplier = signal.health_multiplier if signal else 1.0
            model_attempts = signal.attempt_count if signal else 0

            breakdown = compute_model_score(
                model=row.model,
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
                intent=intent,
                health_multiplier=health_multiplier,
                failure_rate=failure_rate,
                avg_latency_ms=avg_latency_ms,
                observed_latency_ms=observed_latency_ms,
                observed_cost_per_1k_tokens=observed_cost_per_1k,
                prompt_tokens=evaluation.estimated_tokens,
                exploration_enabled=task.discovery_mode,
                model_attempts=model_attempts,
                total_attempts=total_attempts,
            )
            final_total = breakdown.total

            scored.append((
                final_total,
                row.model,
                row,
                tier,
                breakdown,
                snapshot.p50_latency_ms if snapshot else None,
                observed_cost_per_1k,
            ))

        def _tie_key(
            item: tuple[float, ModelProfile, ModelRoutingRow, ModelTier, ScoreBreakdown, float | None, float | None],
        ) -> tuple[float, float, float, float, float, float, str]:
            total_score, model, _row, _tier, breakdown, latency_ms, cost_per_1k = item
            return (
                -total_score,
                -breakdown.health_multiplier,
                -breakdown.context_headroom,
                float(latency_ms) if latency_ms is not None else math.inf,
                float(cost_per_1k) if cost_per_1k is not None else math.inf,
                -breakdown.capability_score,
                model.model_id,
            )

        best_by_model_id: dict[str, tuple[float, ModelProfile, ModelRoutingRow, ModelTier, ScoreBreakdown, float | None, float | None]] = {}
        for item in scored:
            model_id = item[1].model_id
            current = best_by_model_id.get(model_id)
            if current is None or _tie_key(item) < _tie_key(current):
                best_by_model_id[model_id] = item

        deduped = list(best_by_model_id.values())
        deduped.sort(key=_tie_key)
        gap_order = apply_gap_decision(
            ranked_items=[
                (
                    total_score,
                    breakdown.capability_score,
                    breakdown.capability_confidence,
                    model.model_id,
                )
                for total_score, model, _row, _tier, breakdown, _latency_ms, _cost_per_1k in deduped
            ]
        )
        gap_rank = {model_id: idx for idx, model_id in enumerate(gap_order)}
        deduped.sort(
            key=lambda item: (
                gap_rank.get(item[1].model_id, len(gap_rank)),
                *_tie_key(item),
            )
        )

        candidates = [model for _, model, _, _, _, _, _ in deduped]
        score_breakdowns = {model.model_id: breakdown for _, model, _, _, breakdown, _, _ in deduped}

        scored_candidates: list[ScoredCandidate] = []
        for rank, (total_score, model, row, tier, breakdown, p50, _cost_per_1k) in enumerate(deduped, start=1):
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
                    quality_score=float(breakdown.reasoning_score),
                    latency_score=float(breakdown.latency_score),
                    cost_score=float(breakdown.cost_score),
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
