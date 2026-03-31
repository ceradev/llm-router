from __future__ import annotations

import logging

from sqlmodel import Session

from packages.core.analysis.request_analysis import build_request_analysis_draft
from packages.domain.gateway import (
    GatewayExecutionResult,
    GatewayTask,
    InvocationAttempt,
    Priority,
    RankingHighlight,
    RankingSummary,
    RoutedRequest,
    RoutingDecision,
    ScoredCandidate,
    intent_from_evaluation_string,
)
from packages.domain.models import ModelProfile
from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
from packages.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from packages.infrastructure.db.repositories.attempt_repository import AttemptRepository
from packages.infrastructure.db.repositories.evaluation_repository import EvaluationRepository
from packages.infrastructure.db.repositories.execution_repository import ExecutionRepository
from packages.infrastructure.db.repositories.metrics_repository import MetricsRepository
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.repositories.request_repository import RequestRepository
from packages.services.execution.fallback_executor import FallbackExecutor, RoutingExhaustedError
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation import PromptEvaluator, PromptEvaluationResult
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

logger = logging.getLogger(__name__)

_DEPTH_TOKENS = {"short": 256, "balanced": 512, "detailed": 1024}


def _extra_skills_from_evaluation(evaluation: PromptEvaluationResult) -> list[str]:
    tags: list[str] = []
    if evaluation.requires_code:
        tags.append("code")
    if evaluation.requires_json:
        tags.append("json")
    if evaluation.requires_tools:
        tags.append("tools")
    if evaluation.requires_reasoning:
        tags.append("reasoning")
    return tags


class GatewayOrchestrator:
    def __init__(
        self,
        *,
        session: Session,
        model_repository: ModelRepository,
        fallback_registry,
        prompt_evaluator: PromptEvaluator,
        selector: ModelSelector,
        executor: FallbackExecutor,
    ) -> None:
        self.session = session
        self.model_repository = model_repository
        self.fallback_registry = fallback_registry
        self.prompt_evaluator = prompt_evaluator
        self.selector = selector
        self.executor = executor
        self._request_repo = RequestRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        self._eval_repo = EvaluationRepository(session)
        self._execution_repo = ExecutionRepository(session)
        self._attempt_repo = AttemptRepository(session)
        self._metrics_repo = MetricsRepository(session)

    def _maybe_sync_openrouter_catalog(self) -> None:
        settings = get_settings()
        if not settings.openrouter_auto_sync_on_empty_catalog:
            return
        if self.model_repository.count_routing_ready_models(require_json=False) > 0:
            return
        try:
            OpenRouterSyncService(self.session).sync_models()
            self.session.flush()
            logger.info("OpenRouter catalog auto-sync completed")
        except Exception:
            logger.exception("OpenRouter catalog auto-sync failed")

    def list_models(self) -> list[ModelProfile]:
        models = self.model_repository.list_all_models()
        if models:
            return models
        return self.fallback_registry.list_models()

    def execute(self, task: GatewayTask, *, session_id: str | None = None) -> GatewayExecutionResult:
        evaluation = self.prompt_evaluator.evaluate(task.prompt)
        intent = intent_from_evaluation_string(evaluation.intent)
        effective_require_json = task.require_json or evaluation.requires_json
        effective_max_tokens = (
            task.max_tokens
            if task.max_tokens is not None
            else _DEPTH_TOKENS.get(task.response_depth, 512)
        )

        logger.info(
            "prompt_evaluation intent=%s complexity=%.3f requires_code=%s requires_json=%s "
            "requires_tools=%s requires_reasoning=%s",
            evaluation.intent,
            evaluation.complexity_score,
            evaluation.requires_code,
            evaluation.requires_json,
            evaluation.requires_tools,
            evaluation.requires_reasoning,
        )

        llm_req = self._request_repo.create_request(
            prompt=task.prompt,
            intent=intent.value,
            priority=task.priority.value,
            require_json=effective_require_json,
            session_id=session_id,
        )

        draft = build_request_analysis_draft(
            task=task,
            intent=intent,
            complexity_score_override=evaluation.complexity_score,
            tokens_estimated_override=evaluation.estimated_tokens,
            extra_skills=_extra_skills_from_evaluation(evaluation),
            max_tokens_effective=effective_max_tokens,
        )
        self._analysis_repo.save_analysis(
            llm_req.id,
            task_type=draft.task_type,
            complexity_score=draft.complexity_score,
            cost_sensitivity=draft.cost_sensitivity,
            latency_sensitivity=draft.latency_sensitivity,
            detected_skills=draft.detected_skills,
            tokens_estimated=draft.tokens_estimated,
        )

        self._maybe_sync_openrouter_catalog()
        decision = self.selector.build_decision(
            task=task,
            intent=intent,
            evaluation=evaluation,
            require_json=effective_require_json,
        )

        evaluations = [
            ModelEvaluation(
                request_id=llm_req.id,
                model_id=sc.db_model_id,
                quality_score=sc.quality_score,
                latency_score=sc.latency_score,
                cost_score=sc.cost_score,
                final_score=sc.final_score,
                evaluation_rank=sc.rank,
                explanation=sc.explanation,
                pros=list(sc.pros) if sc.pros else None,
                cons=list(sc.cons) if sc.cons else None,
            )
            for sc in decision.scored_candidates
        ]
        self._eval_repo.bulk_insert_evaluations(evaluations)

        routed = RoutedRequest(
            prompt=task.prompt,
            temperature=decision.applied_temperature,
            max_tokens=effective_max_tokens,
            require_json=effective_require_json,
            simulate_failures=set(task.simulate_failures),
        )

        attempt_order = 0

        def on_attempt(att: InvocationAttempt) -> None:
            nonlocal attempt_order
            attempt_order += 1
            self._attempt_repo.save_attempt(
                request_id=llm_req.id,
                provider_slug=att.provider,
                model_routing_key=att.model_id,
                attempt_order=attempt_order,
                status=att.status,
                error=att.detail if att.status != "success" else None,
                latency_ms=att.latency_ms,
            )

        try:
            outcome = self.executor.run(
                request=routed,
                decision=decision,
                on_attempt=on_attempt,
            )
        except RoutingExhaustedError as exc:
            self._metrics_repo.record_request(
                session_id=session_id,
                success=False,
                latency_ms=0,
            )
            raise RoutingExhaustedError(
                exc.attempts,
                exc.reason,
                request_id=llm_req.id,
                scored_candidates=decision.scored_candidates,
            ) from exc

        win_id = self.model_repository.get_model_id_by_routing_key(outcome.response.model_id)
        if win_id is None:
            raise RuntimeError(f"Unknown routing key after success: {outcome.response.model_id}")

        self._execution_repo.save_execution(
            request_id=llm_req.id,
            model_id=win_id,
            input_tokens=outcome.response.input_tokens or 0,
            output_tokens=outcome.response.output_tokens or 0,
            latency_ms=outcome.response.latency_ms or 0,
            cost=outcome.response.cost,
            success=True,
            error=None,
        )

        fallback_used = len(outcome.attempts) > 1 or (
            bool(decision.candidates) and outcome.response.model_id != decision.candidates[0].model_id
        )
        self._request_repo.update_request_outcome(
            llm_req.id,
            selected_model_id=win_id,
            fallback_used=fallback_used,
        )

        self._metrics_repo.record_request(
            session_id=session_id,
            success=True,
            latency_ms=outcome.response.latency_ms or 0,
        )

        ranking_summary = _build_ranking_summary(decision, priority=task.priority)

        return GatewayExecutionResult(
            request_id=llm_req.id,
            response=outcome.response,
            decision=decision,
            attempts=outcome.attempts,
            fallback_used=fallback_used,
            ranking_summary=ranking_summary,
        )


_ECONOMICAL_COST_SCORE = 4
_FREE_ALT_MIN_SCORE_RATIO = 0.72


def _display_name(model_id: str) -> str:
    return model_id.split("/")[-1].replace("-", " ").title()


def _best_overall_reason_key(priority: Priority) -> str:
    return {
        Priority.BALANCED: "rankingReasonBestOverallBalanced",
        Priority.HIGH_QUALITY: "rankingReasonBestOverallHighQuality",
        Priority.LOW_COST: "rankingReasonBestOverallLowCost",
        Priority.LOW_LATENCY: "rankingReasonBestOverallLowLatency",
    }[priority]


def _highlight_from_candidate(
    candidate: ScoredCandidate,
    *,
    reason_key: str,
    same_as_best_overall: bool = False,
) -> RankingHighlight:
    return RankingHighlight(
        model_id=candidate.model.model_id,
        display_name=_display_name(candidate.model.model_id),
        provider=candidate.model.provider,
        reason_key=reason_key,
        same_as_best_overall=same_as_best_overall,
    )


def _argmax_candidate(
    candidates: tuple[ScoredCandidate, ...],
    *,
    key,
) -> ScoredCandidate:
    return max(candidates, key=lambda c: (key(c), c.final_score, c.model.model_id))


def _pick_free_alternative(best: ScoredCandidate, rest: tuple[ScoredCandidate, ...]) -> ScoredCandidate | None:
    if best.model.cost_score >= _ECONOMICAL_COST_SCORE:
        return None
    economical = [c for c in rest if c.model.cost_score >= _ECONOMICAL_COST_SCORE]
    if not economical:
        return None
    economical.sort(key=lambda c: (-c.final_score, c.model.model_id))
    pick = economical[0]
    if pick.final_score < best.final_score * _FREE_ALT_MIN_SCORE_RATIO:
        return None
    return pick


def _build_ranking_summary(decision: RoutingDecision, *, priority: Priority) -> RankingSummary:
    candidates = decision.scored_candidates
    if not candidates:
        placeholder = RankingHighlight(
            model_id="",
            display_name="",
            provider="",
            reason_key="rankingReasonNoRanking",
            same_as_best_overall=False,
        )
        return RankingSummary(
            best_overall=placeholder,
            free_alternative=None,
            best_quality=placeholder,
            best_cost=placeholder,
            best_speed=placeholder,
        )

    best = candidates[0]
    rest = candidates[1:]

    best_h = _highlight_from_candidate(best, reason_key=_best_overall_reason_key(priority))

    free_pick = _pick_free_alternative(best, rest)
    free_h = (
        _highlight_from_candidate(free_pick, reason_key="rankingReasonFreeAlternative")
        if free_pick is not None
        else None
    )

    q = _argmax_candidate(candidates, key=lambda c: c.quality_score)
    co = _argmax_candidate(candidates, key=lambda c: c.cost_score)
    sp = _argmax_candidate(candidates, key=lambda c: c.latency_score)

    return RankingSummary(
        best_overall=best_h,
        free_alternative=free_h,
        best_quality=_highlight_from_candidate(
            q,
            reason_key="rankingReasonCategoryQuality",
            same_as_best_overall=q.model.model_id == best.model.model_id,
        ),
        best_cost=_highlight_from_candidate(
            co,
            reason_key="rankingReasonCategoryCost",
            same_as_best_overall=co.model.model_id == best.model.model_id,
        ),
        best_speed=_highlight_from_candidate(
            sp,
            reason_key="rankingReasonCategorySpeed",
            same_as_best_overall=sp.model.model_id == best.model.model_id,
        ),
    )
