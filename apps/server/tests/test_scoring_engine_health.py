from __future__ import annotations

import pytest

from packages.domain.gateway import Priority
from packages.domain.models import ModelProfile, Capability
from packages.core.scoring.engine import compute_model_score


def _base_model() -> ModelProfile:
    return ModelProfile(
        model_id="test-model",
        provider="openai",
        quality_score=8,
        latency_score=7,
        cost_score=9,
        default_temperature=0.7,
        capabilities={Capability.CODE},
        supports_tools=True,
    )


class TestHealthMultiplier:
    def test_health_effective_is_softened_and_bounded(self):
        model = _base_model()
        degraded = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.35,
        )
        healthy = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.0,
        )
        assert degraded.health_effective == pytest.approx(0.74)
        assert healthy.health_effective == pytest.approx(1.0)
        assert degraded.total < healthy.total

    def test_failure_rate_and_latency_feed_health_multiplier(self):
        model = _base_model()
        baseline = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
        )
        degraded = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            failure_rate=0.7,
            avg_latency_ms=7000.0,
        )
        assert degraded.health_multiplier < baseline.health_multiplier
        assert degraded.total < baseline.total

    def test_feedback_effective_is_softened_and_bounded(self):
        model = _base_model()
        low = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            avg_rating=1.0,
            ratings_count=200,
        )
        high = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            avg_rating=5.0,
            ratings_count=200,
        )
        assert 0.95 <= low.feedback_effective <= 1.05
        assert 0.95 <= high.feedback_effective <= 1.05
        assert high.total > low.total
