from __future__ import annotations

import pytest

from packages.core.scoring.engine import (
    CapabilityRoutingConfig,
    adjust_score_with_capability,
    apply_gap_decision,
    compute_model_score,
    should_apply_low_tier_penalty,
)
from packages.domain.gateway import Priority
from packages.domain.models import Capability, ModelProfile


def _profile(**overrides: object) -> ModelProfile:
    base: dict[str, object] = {
        "model_id": "openai/test",
        "provider": "openai",
        "quality_score": 6,
        "latency_score": 6,
        "cost_score": 6,
        "default_temperature": 0.2,
        "capabilities": {Capability.GENERAL},
        "supports_tools": False,
        "context_window": 8192,
        "prompt_price": 0.000002,
        "completion_price": 0.000006,
        "evaluation_status": "verified",
    }
    base.update(overrides)
    return ModelProfile(**base)  # type: ignore[arg-type]


def test_compute_model_score_prefers_higher_total() -> None:
    low = _profile(model_id="p/low", quality_score=1, latency_score=1, cost_score=1)
    high = _profile(model_id="p/high", quality_score=10, latency_score=10, cost_score=10)

    low_score = compute_model_score(model=low, priority=Priority.BALANCED, priority_weight=100).total
    high_score = compute_model_score(model=high, priority=Priority.BALANCED, priority_weight=100).total

    assert high_score > low_score


def test_context_score_is_monotonic_with_context_window() -> None:
    small_ctx = _profile(model_id="ctx/small", context_window=4096)
    large_ctx = _profile(model_id="ctx/large", context_window=32768)

    small = compute_model_score(
        model=small_ctx,
        priority=Priority.BALANCED,
        priority_weight=100,
        prompt_tokens=3000,
    )
    large = compute_model_score(
        model=large_ctx,
        priority=Priority.BALANCED,
        priority_weight=100,
        prompt_tokens=3000,
    )
    assert large.context_score >= small.context_score


def test_feedback_factor_is_bounded_and_stable_for_small_n() -> None:
    model = _profile()
    base = compute_model_score(model=model, priority=Priority.BALANCED, priority_weight=100)
    tiny_sample = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=100,
        avg_rating=5.0,
        ratings_count=1,
    )
    assert tiny_sample.feedback_effective <= 1.05
    assert tiny_sample.total - base.total < 0.1


def test_no_score_collapse_low_values() -> None:
    weak = _profile(model_id="m/weak", quality_score=1, latency_score=1, cost_score=1, context_window=4096)
    weak_plus = _profile(model_id="m/weak-plus", quality_score=1, latency_score=2, cost_score=1, context_window=4096)
    s1 = compute_model_score(
        model=weak,
        priority=Priority.BALANCED,
        priority_weight=50,
        prompt_tokens=3500,
    )
    s2 = compute_model_score(
        model=weak_plus,
        priority=Priority.BALANCED,
        priority_weight=50,
        prompt_tokens=3500,
    )
    assert s2.total > s1.total
    assert abs(s2.total - s1.total) > 1e-6


def test_complexity_increases_capability_influence() -> None:
    model = _profile(
        model_id="cap/high-complexity",
        tier="premium",
        capabilities={Capability.GENERAL, Capability.CODE, Capability.ANALYSIS},
        evaluation_status="verified",
    )
    low_complexity = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=100,
        complexity_score=0.2,
        requires_reasoning=True,
        capability_score=0.86,
    )
    high_complexity = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=100,
        complexity_score=0.9,
        requires_reasoning=True,
        capability_score=0.86,
    )
    assert high_complexity.capability_adjustment > low_complexity.capability_adjustment


def test_low_tier_overperformance_gets_penalized() -> None:
    budget_model = _profile(
        model_id="budget/model",
        tier="budget",
        evaluation_status="cataloged",
    )
    _score, budget_adjustment, _confidence = adjust_score_with_capability(
        model=budget_model,
        current_score=1.92,
        capability_score=0.40,
        reasoning_score=0.85,
        complexity_score=0.4,
    )
    assert budget_adjustment < 0.0


def test_gap_decision_prefers_higher_capability_when_scores_are_close() -> None:
    ordered = apply_gap_decision(
        ranked_items=[
            (1.02, 0.55, 0.80, "budget/model"),
            (1.01, 0.90, 1.00, "premium/model"),
        ],
        gap_threshold=0.02,
    )
    assert ordered[0] == "premium/model"


def test_low_tier_penalty_requires_low_confidence() -> None:
    model = _profile(model_id="budget/penalty-check", tier="budget")
    cfg = CapabilityRoutingConfig()
    should_penalize = should_apply_low_tier_penalty(
        model=model,
        score=0.9,
        expected=0.5,
        confidence=0.6,
        config=cfg,
    )
    should_not_penalize = should_apply_low_tier_penalty(
        model=model,
        score=0.9,
        expected=0.5,
        confidence=0.95,
        config=cfg,
    )
    assert should_penalize is True
    assert should_not_penalize is False


def test_capability_total_delta_is_capped() -> None:
    model = _profile(
        model_id="cap/cap-check",
        tier="premium",
        evaluation_status="verified",
    )
    scored = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=100,
        complexity_score=1.0,
        requires_reasoning=True,
        capability_score=1.0,
    )
    assert abs(scored.capability_prior + scored.capability_adjustment) <= 0.100001


def test_capability_reason_is_set() -> None:
    model = _profile(
        model_id="cap/reason",
        tier="budget",
        evaluation_status="cataloged",
    )
    scored = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=100,
        complexity_score=0.9,
        requires_reasoning=True,
        capability_score=0.35,
    )
    assert scored.capability_reason in {
        "premium_near_tie_boost",
        "low_confidence_penalty",
        "complexity_boost",
        "none",
    }

