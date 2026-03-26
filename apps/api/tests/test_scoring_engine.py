from __future__ import annotations

from packages.core.scoring.engine import compute_model_score
from packages.domain.gateway import Priority
from packages.domain.models import Capability, ModelProfile


def test_compute_model_score_prefers_higher_total() -> None:
    low = ModelProfile(
        model_id="p/low",
        provider="p",
        quality_score=1,
        latency_score=1,
        cost_score=1,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )
    high = ModelProfile(
        model_id="p/high",
        provider="p",
        quality_score=5,
        latency_score=5,
        cost_score=5,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )

    low_score = compute_model_score(model=low, priority=Priority.BALANCED, priority_weight=100).total
    high_score = compute_model_score(model=high, priority=Priority.BALANCED, priority_weight=100).total

    assert high_score > low_score


def test_compute_model_score_includes_priority_weight() -> None:
    base = ModelProfile(
        model_id="p/m",
        provider="p",
        quality_score=3,
        latency_score=3,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )

    low = compute_model_score(model=base, priority=Priority.BALANCED, priority_weight=50).total
    high = compute_model_score(model=base, priority=Priority.BALANCED, priority_weight=150).total

    assert high > low

