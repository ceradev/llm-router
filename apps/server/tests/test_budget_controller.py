# apps/server/tests/test_budget_controller.py
from __future__ import annotations

import pytest
from packages.domain.gateway import ScoredCandidate, ModelTier, HealthState
from packages.domain.models import ModelProfile, Capability
from packages.services.budget.controller import BudgetConstraint, BudgetController


def _make_model(
    model_id: str,
    prompt_price: float,
    completion_price: float,
) -> ModelProfile:
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


def _make_candidate(model: ModelProfile, rank: int) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=1.0,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER2_PROVISIONAL,
        health_status=HealthState.HEALTHY,
    )


class TestBudgetController:
    def setup_method(self):
        self.ctrl = BudgetController()

    def test_no_limit_returns_all(self):
        expensive = _make_model("gpt-4", prompt_price=0.01, completion_price=0.03)
        cheap = _make_model("gpt-3.5", prompt_price=0.001, completion_price=0.002)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(cheap, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=None,
            estimated_input_tokens=1000,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert result == candidates

    def test_filters_over_budget_candidate(self):
        # expensive: 1000 * 0.01 + 512 * 0.03 = 10 + 15.36 = 25.36 USD
        expensive = _make_model("gpt-4", prompt_price=0.01, completion_price=0.03)
        # cheap: 1000 * 0.0001 + 512 * 0.0002 = 0.1 + 0.1024 = 0.2024 USD
        cheap = _make_model("gpt-3.5", prompt_price=0.0001, completion_price=0.0002)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(cheap, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=1.0,
            estimated_input_tokens=1000,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 1
        assert result[0].model.model_id == "gpt-3.5"

    def test_all_over_budget_returns_all_unchanged(self):
        """Safety: never starve the pipeline entirely."""
        expensive = _make_model("gpt-4", prompt_price=1.0, completion_price=1.0)
        also_expensive = _make_model("claude-3", prompt_price=0.9, completion_price=0.9)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(also_expensive, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=0.001,
            estimated_input_tokens=100,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 2

    def test_estimate_cost_no_pricing_returns_zero(self):
        free_model = _make_model("free-model", prompt_price=0.0, completion_price=0.0)
        constraint = BudgetConstraint(max_estimated_cost_usd=None, estimated_input_tokens=500)
        cost = self.ctrl.estimate_cost(free_model, constraint)
        assert cost == 0.0

    def test_estimate_cost_calculation(self):
        model = _make_model("gpt-4o", prompt_price=0.000005, completion_price=0.000015)
        constraint = BudgetConstraint(
            max_estimated_cost_usd=None,
            estimated_input_tokens=1000,
            estimated_output_tokens=200,
        )
        cost = self.ctrl.estimate_cost(model, constraint)
        # 1000 * 0.000005 + 200 * 0.000015 = 0.005 + 0.003 = 0.008
        assert abs(cost - 0.008) < 1e-9
