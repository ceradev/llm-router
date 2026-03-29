from __future__ import annotations

from packages.core.scoring.engine import ScoreBreakdown, compute_model_score
from packages.domain.gateway import (
    GatewayTask,
    Intent,
    NoModelsAvailableError,
    Priority,
    RoutingDecision,
    ScoredCandidate,
)
from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow
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
    def __init__(self, *, model_repository: ModelRepository) -> None:
        self.model_repository = model_repository

    def build_decision(
        self,
        *,
        task: GatewayTask,
        intent: Intent,
        evaluation: PromptEvaluationResult,
        require_json: bool | None = None,
    ) -> RoutingDecision:
        effective_json = task.require_json if require_json is None else require_json
        db_rows = self._load_candidates(priority=task.priority, require_json=effective_json)
        candidates, scored_candidates, score_breakdowns = self._rank_candidates(
            task=task,
            rows=db_rows,
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
            require_json=effective_json,
            ranked=candidates,
            evaluation=evaluation,
            score_breakdowns=score_breakdowns,
        )

        return RoutingDecision(
            intent=intent,
            reason=reason,
            applied_temperature=temperature,
            candidates=candidates,
            scored_candidates=scored_candidates,
        )

    def _load_candidates(
        self,
        *,
        priority: Priority,
        require_json: bool,
    ) -> list[ModelRoutingRow]:
        return self.model_repository.list_routing_candidates(priority=priority, require_json=require_json)

    def _rank_candidates(
        self,
        *,
        task: GatewayTask,
        rows: list[ModelRoutingRow],
        priority: Priority,
        evaluation: PromptEvaluationResult,
    ) -> tuple[list[ModelProfile], tuple[ScoredCandidate, ...], dict[str, ScoreBreakdown]]:
        scored: list[tuple[float, ModelProfile, ModelRoutingRow, ScoreBreakdown]] = []
        for row in rows:
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
            )
            scored.append((breakdown.total, row.model, row, breakdown))

        scored.sort(key=lambda item: (-item[0], item[1].model_id))
        candidates = [model for _, model, _, _ in scored]
        score_breakdowns = {model.model_id: breakdown for _, model, _, breakdown in scored}

        scored_candidates: list[ScoredCandidate] = []
        for rank, (_, model, row, breakdown) in enumerate(scored, start=1):
            pros, cons = _pros_cons_for(model=model, priority=priority)
            scored_candidates.append(
                ScoredCandidate(
                    model=model,
                    priority_weight=row.priority_weight,
                    db_model_id=row.db_model_id,
                    rank=rank,
                    quality_score=float(model.quality_score),
                    latency_score=float(model.latency_score),
                    cost_score=float(model.cost_score),
                    final_score=breakdown.total,
                    explanation=breakdown.explanation,
                    pros=pros,
                    cons=cons,
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
        require_json: bool,
        ranked: list[ModelProfile],
        evaluation: PromptEvaluationResult,
        score_breakdowns: dict[str, ScoreBreakdown],
    ) -> str:
        short_name = primary_model.split("/")[-1].replace("-", " ").title()
        intent_str = intent.value.replace("_", " ").title()
        priority_str = priority.value.replace("_", " ").title()

        reason = f"Selected '{short_name}' for {intent_str.lower()} task with {priority_str.lower()} priority"
        
        if ranked:
            bd = score_breakdowns.get(primary_model)
            if bd and bd.total > 0:
                reason += f". Best overall score: {bd.total:.2f}"

        return reason
