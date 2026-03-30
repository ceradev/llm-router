"""Heuristic (metadata-only) screening: promotes to `provisional`, never to `verified`.

`verified` requires a live benchmark (`benchmark_kind=live` in `model_benchmark_runs`).

Active evaluation scope (v1)
----------------------------
Only **text → text** models are screened. Multimodal models are `skipped_unsupported`.

Promotion policy (heuristic)
----------------------------
- **cataloged** / **provisional** / **rejected** + pass → **`provisional`**; routing stays **off** (scores stored for later live verification).
- **cataloged** / **provisional** / **rejected** + fail → **`rejected`**.
- **skipped** (unsupported modality) → state unchanged (**cataloged** typically).
- **`verified`**: heuristic not applicable (use live benchmark); skipped run recorded.
- **`deprecated`**: skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from packages.core.openrouter.pricing import compute_cost_score
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import (
    BenchmarkKind,
    BenchmarkRunStatus,
    BenchmarkScope,
    ModelBenchmarkRun,
)

CURRENT_HEURISTIC_VERSION = "benchmark-heuristic-v1"

_NON_TEXT_MODALITIES = frozenset({"image", "audio", "video", "file"})


def is_active_text_to_text_evaluation_scope(model: LLMModel) -> bool:
    """Return True if the model is in scope for v1 text-only benchmark logic."""

    if model.supports_vision:
        return False

    def _modalities(xs: list[str] | None) -> set[str]:
        if not xs:
            return {"text"}
        return {str(x).lower() for x in xs}

    ins = _modalities(model.input_modalities)
    outs = _modalities(model.output_modalities)
    if ins & _NON_TEXT_MODALITIES:
        return False
    if outs & _NON_TEXT_MODALITIES:
        return False
    return True


@dataclass(frozen=True)
class ComputedBenchmarkScores:
    quality_score: int
    latency_score: int
    cost_score: int
    json_reliability: float
    tool_reliability: float
    error_rate: float


def _total_price(model: LLMModel) -> float:
    p = model.prompt_price
    c = model.completion_price
    total = 0.0
    if p is not None:
        total += float(p)
    if c is not None:
        total += float(c)
    return total


def compute_deterministic_scores(model: LLMModel) -> ComputedBenchmarkScores:
    """Derive routing-aligned integer scores and reliability proxies from catalog fields."""

    cost_score = compute_cost_score(_total_price(model))
    tier = (model.tier or "alternative").strip().lower()
    if tier == "premium":
        quality_score = 5
        latency_score = 3
    elif tier == "free":
        quality_score = 2
        latency_score = 4
    else:
        quality_score = 3
        latency_score = 4

    if model.context_window is not None and model.context_window >= 100_000:
        quality_score = min(5, quality_score + 1)

    json_reliability = 1.0 if model.supports_json else 0.4
    tool_reliability = 1.0 if model.supports_tools else 0.6

    return ComputedBenchmarkScores(
        quality_score=quality_score,
        latency_score=latency_score,
        cost_score=cost_score,
        json_reliability=json_reliability,
        tool_reliability=tool_reliability,
        error_rate=0.0,
    )


def passes_minimum_thresholds(scores: ComputedBenchmarkScores) -> bool:
    """v1 gate: integer routing scores 1–5 and tolerances on reliability."""

    if scores.error_rate > 0.05:
        return False
    if scores.quality_score < 2 or scores.latency_score < 2 or scores.cost_score < 2:
        return False
    if scores.json_reliability < 0.35 or scores.tool_reliability < 0.35:
        return False
    return True


@dataclass(frozen=True)
class BenchmarkOutcome:
    benchmark_run_id: int
    status: BenchmarkRunStatus
    passed: bool
    evaluation_status_after: ModelEvaluationStatus


class ModelBenchmarkService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def run_heuristic_screening(self, *, model_id: int) -> BenchmarkOutcome:
        """Metadata-only screening. Does not call providers. Max outcome: `provisional`."""

        model = self._session.get(LLMModel, model_id)
        if model is None:
            raise ValueError(f"model id {model_id} not found")

        if model.evaluation_status == ModelEvaluationStatus.DEPRECATED:
            row = self._persist_run(
                model_id=model_id,
                benchmark_kind=BenchmarkKind.HEURISTIC,
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                scores=None,
                summary="Heuristic screening skipped: deprecated models are not evaluated.",
                raw={
                    "reason": "deprecated",
                    "evaluation_scope": "text_to_text_v1",
                    "benchmark_scope": BenchmarkScope.TEXT.value,
                },
            )
            self._session.flush()
            return BenchmarkOutcome(
                benchmark_run_id=row.id,  # type: ignore[arg-type]
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                passed=False,
                evaluation_status_after=model.evaluation_status,
            )

        if model.evaluation_status == ModelEvaluationStatus.VERIFIED:
            row = self._persist_run(
                model_id=model_id,
                benchmark_kind=BenchmarkKind.HEURISTIC,
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                scores=None,
                summary="Heuristic screening skipped: model is already execution-verified; use live benchmark to refresh.",
                raw={
                    "reason": "already_verified",
                    "evaluation_scope": "text_to_text_v1",
                    "benchmark_scope": BenchmarkScope.TEXT.value,
                },
            )
            self._session.flush()
            return BenchmarkOutcome(
                benchmark_run_id=row.id,  # type: ignore[arg-type]
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                passed=False,
                evaluation_status_after=model.evaluation_status,
            )

        if not is_active_text_to_text_evaluation_scope(model):
            row = self._persist_run(
                model_id=model_id,
                benchmark_kind=BenchmarkKind.HEURISTIC,
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                scores=None,
                summary="Heuristic screening skipped: multimodal or out-of-scope for text→text v1.",
                raw={
                    "reason": "unsupported_modality",
                    "supports_vision": model.supports_vision,
                    "input_modalities": model.input_modalities,
                    "output_modalities": model.output_modalities,
                    "evaluation_scope": "text_to_text_v1",
                    "benchmark_scope": BenchmarkScope.TEXT.value,
                },
            )
            self._session.flush()
            self._disable_routing(model_id=model_id)
            return BenchmarkOutcome(
                benchmark_run_id=row.id,  # type: ignore[arg-type]
                status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
                passed=False,
                evaluation_status_after=model.evaluation_status,
            )

        scores = compute_deterministic_scores(model)
        ok = passes_minimum_thresholds(scores)
        raw: dict[str, Any] = {
            "evaluation_version": CURRENT_HEURISTIC_VERSION,
            "benchmark_kind": BenchmarkKind.HEURISTIC.value,
            "evaluation_scope": "text_to_text_v1",
            "benchmark_scope": BenchmarkScope.TEXT.value,
            "deterministic": True,
            "scores": {
                "quality_score": scores.quality_score,
                "latency_score": scores.latency_score,
                "cost_score": scores.cost_score,
                "json_reliability": scores.json_reliability,
                "tool_reliability": scores.tool_reliability,
                "error_rate": scores.error_rate,
            },
            "passed_thresholds": ok,
        }

        bench_status = BenchmarkRunStatus.COMPLETED if ok else BenchmarkRunStatus.FAILED
        summary = (
            "Heuristic screening passed; catalog state provisional (not execution-verified)."
            if ok
            else "Heuristic screening failed thresholds."
        )

        row = self._persist_run(
            model_id=model_id,
            benchmark_kind=BenchmarkKind.HEURISTIC,
            status=bench_status,
            scores=scores,
            summary=summary,
            raw=raw,
        )
        self._session.flush()

        if ok:
            self._apply_heuristic_pass(model=model, scores=scores)
        else:
            self._apply_heuristic_fail(model=model)

        self._session.add(model)
        self._session.flush()

        return BenchmarkOutcome(
            benchmark_run_id=row.id,  # type: ignore[arg-type]
            status=bench_status,
            passed=ok,
            evaluation_status_after=model.evaluation_status,
        )

    def run_benchmark_for_model(self, *, model_id: int) -> BenchmarkOutcome:
        """Backward-compatible alias for heuristic screening."""

        return self.run_heuristic_screening(model_id=model_id)

    def _persist_run(
        self,
        *,
        model_id: int,
        benchmark_kind: BenchmarkKind,
        status: BenchmarkRunStatus,
        scores: ComputedBenchmarkScores | None,
        summary: str,
        raw: dict[str, Any],
    ) -> ModelBenchmarkRun:
        kind_val = benchmark_kind.value
        if scores is None:
            run = ModelBenchmarkRun(
                model_id=model_id,
                evaluation_version=CURRENT_HEURISTIC_VERSION,
                benchmark_kind=kind_val,
                benchmark_scope=BenchmarkScope.TEXT.value,
                status=status.value,
                quality_score=0,
                latency_score=0,
                cost_score=0,
                json_reliability=0.0,
                tool_reliability=0.0,
                error_rate=0.0,
                sample_size=0,
                summary=summary,
                raw_results_json=raw,
            )
        else:
            run = ModelBenchmarkRun(
                model_id=model_id,
                evaluation_version=CURRENT_HEURISTIC_VERSION,
                benchmark_kind=kind_val,
                benchmark_scope=BenchmarkScope.TEXT.value,
                status=status.value,
                quality_score=scores.quality_score,
                latency_score=scores.latency_score,
                cost_score=scores.cost_score,
                json_reliability=scores.json_reliability,
                tool_reliability=scores.tool_reliability,
                error_rate=scores.error_rate,
                sample_size=1,
                summary=summary,
                raw_results_json=raw,
            )
        self._session.add(run)
        return run

    def _disable_routing(self, *, model_id: int) -> None:
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model_id)
        rs = self._session.exec(stmt).first()
        if rs is None:
            self._session.add(
                LLMModelRoutingSettings(
                    model_id=model_id,
                    quality_score=0,
                    latency_score=0,
                    cost_score=0,
                    default_temperature=0.2,
                    priority_weight=100,
                    allow_fallback=True,
                    enabled_for_routing=False,
                    is_evaluated_for_routing=False,
                )
            )
            return
        rs.enabled_for_routing = False
        rs.is_evaluated_for_routing = False
        self._session.add(rs)

    def _apply_heuristic_pass(self, *, model: LLMModel, scores: ComputedBenchmarkScores) -> None:
        now = datetime.now(timezone.utc)
        model.evaluation_status = ModelEvaluationStatus.PROVISIONAL
        model.evaluation_confidence = 0.6
        model.last_evaluated_at = now
        model.evaluation_version = CURRENT_HEURISTIC_VERSION

        assert model.id is not None
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model.id)
        rs = self._session.exec(stmt).first()
        if rs is None:
            self._session.add(
                LLMModelRoutingSettings(
                    model_id=model.id,
                    quality_score=scores.quality_score,
                    latency_score=scores.latency_score,
                    cost_score=scores.cost_score,
                    default_temperature=0.2,
                    priority_weight=100,
                    allow_fallback=True,
                    enabled_for_routing=False,
                    is_evaluated_for_routing=False,
                )
            )
            return

        rs.quality_score = scores.quality_score
        rs.latency_score = scores.latency_score
        rs.cost_score = scores.cost_score
        rs.is_evaluated_for_routing = False
        rs.enabled_for_routing = False
        self._session.add(rs)

    def _apply_heuristic_fail(self, *, model: LLMModel) -> None:
        now = datetime.now(timezone.utc)
        model.evaluation_status = ModelEvaluationStatus.REJECTED
        model.evaluation_confidence = 0.0
        model.last_evaluated_at = now
        model.evaluation_version = CURRENT_HEURISTIC_VERSION

        assert model.id is not None
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model.id)
        rs = self._session.exec(stmt).first()
        if rs is None:
            self._session.add(
                LLMModelRoutingSettings(
                    model_id=model.id,
                    quality_score=0,
                    latency_score=0,
                    cost_score=0,
                    default_temperature=0.2,
                    priority_weight=100,
                    allow_fallback=True,
                    enabled_for_routing=False,
                    is_evaluated_for_routing=False,
                )
            )
            return
        rs.enabled_for_routing = False
        rs.is_evaluated_for_routing = False
        self._session.add(rs)
