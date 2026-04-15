"""Integration test for the dynamic feedback loop pipeline.

Tests that RealTimeObserver health signals + BudgetController filtering
integrate correctly through GatewayOrchestrator without a live database.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from packages.domain.gateway import (
    GatewayTask,
    Priority,
    ScoredCandidate,
    ModelTier,
    HealthState,
    RoutingDecision,
    Intent,
    ProviderResponse,
    FallbackExecutionOutcome,
    InvocationAttempt,
)
from packages.domain.models import ModelProfile, Capability
from packages.services.budget.controller import BudgetConstraint, BudgetController
from packages.services.real_time_observer.types import RealTimeHealthSnapshot, ModelHealthSignal
from packages.services.orchestration.orchestrator import _apply_health_to_candidates


def _make_model(model_id: str, prompt_price: float = 0.0, completion_price: float = 0.0) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities=set(),
        supports_tools=False,
        prompt_price=prompt_price,
        completion_price=completion_price,
    )


def _make_candidate(model: ModelProfile, rank: int, score: float) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=score,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER1_VERIFIED,
        health_status=HealthState.HEALTHY,
    )


class TestFullFeedbackLoopPipeline:
    def test_health_degradation_plus_budget_filter(self):
        """Top model is degraded → re-ranked below alt. Alt exceeds budget → filtered.
        Result: degraded model (still within budget at reduced score) survives.
        """
        # Model A: expensive, initially top-ranked but degraded
        model_a = _make_model("openai/gpt-4", prompt_price=0.01, completion_price=0.03)
        # Model B: cheap, initially rank-2
        model_b = _make_model("google/gemini-flash", prompt_price=0.00001, completion_price=0.00002)

        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.5),
        )

        # Health: model_a is severely degraded
        signals = {
            "openai/gpt-4": ModelHealthSignal(
                model_routing_key="openai/gpt-4",
                failure_rate=0.8,
                avg_latency_ms=None,
                attempt_count=10,
                health_multiplier=0.44,  # 1 - 0.8*0.7 = 0.44
            )
        }
        observer = MagicMock()
        observer.get_health_snapshot.return_value = RealTimeHealthSnapshot(signals=signals)

        # Step 1: health re-ranking
        health_adjusted = _apply_health_to_candidates(candidates, observer)
        # gpt-4: 2.0 * 0.44 = 0.88, gemini: 1.5 (unchanged) → gemini now rank 1
        assert health_adjusted[0].model.model_id == "google/gemini-flash"

        # Step 2: budget filtering — budget set to $5 max
        # gpt-4 cost: 1000*0.01 + 512*0.03 = $25.36 → over budget
        # gemini cost: 1000*0.00001 + 512*0.00002 = $0.02 → within budget
        ctrl = BudgetController()
        constraint = BudgetConstraint(
            max_estimated_cost_usd=5.0,
            estimated_input_tokens=1000,
            estimated_output_tokens=512,
        )
        budget_filtered = ctrl.filter_candidates(health_adjusted, constraint)
        assert len(budget_filtered) == 1
        assert budget_filtered[0].model.model_id == "google/gemini-flash"

    def test_no_health_data_no_budget_passthrough(self):
        """With no health signals and no budget limit, pipeline is transparent."""
        model_a = _make_model("openai/gpt-4")
        model_b = _make_model("anthropic/claude-3")
        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.5),
        )
        observer = MagicMock()
        observer.get_health_snapshot.return_value = RealTimeHealthSnapshot(signals={})

        health_adjusted = _apply_health_to_candidates(candidates, observer)
        assert health_adjusted == candidates  # unchanged

        ctrl = BudgetController()
        constraint = BudgetConstraint(max_estimated_cost_usd=None, estimated_input_tokens=500)
        result = ctrl.filter_candidates(health_adjusted, constraint)
        assert result == candidates

    def test_all_candidates_over_budget_safety_passthrough(self):
        """Safety: if every model exceeds budget, return all unchanged."""
        expensive_a = _make_model("a/model", prompt_price=1.0, completion_price=1.0)
        expensive_b = _make_model("b/model", prompt_price=0.9, completion_price=0.9)
        candidates = (
            _make_candidate(expensive_a, 1, 2.0),
            _make_candidate(expensive_b, 2, 1.5),
        )
        ctrl = BudgetController()
        constraint = BudgetConstraint(
            max_estimated_cost_usd=0.001,
            estimated_input_tokens=100,
        )
        result = ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 2  # Safety: no starvation
