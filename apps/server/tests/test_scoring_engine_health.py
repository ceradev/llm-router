from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import Priority, Intent
from packages.domain.models import ModelProfile, Capability
from packages.core.scoring.engine import compute_model_score


def _base_model() -> ModelProfile:
    return ModelProfile(
        model_id="test-model",
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities={Capability.CODE},
        supports_tools=True,
    )


class TestHealthMultiplier:
    def test_full_health_does_not_penalize(self):
        model = _base_model()
        healthy = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.0,
        )
        no_param = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
        )
        assert abs(healthy.base_total - no_param.base_total) < 1e-9

    def test_degraded_health_reduces_base_total(self):
        model = _base_model()
        healthy = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.0,
        )
        degraded = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.6,
        )
        assert degraded.base_total < healthy.base_total
        assert abs(degraded.base_total - healthy.base_total * 0.6) < 1e-6

    def test_health_multiplier_clamped_to_minimum_0_3(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.0,   # Should be clamped to 0.3
        )
        assert breakdown.health_multiplier == 0.3

    def test_health_multiplier_clamped_to_maximum_1_0(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.5,   # Should be clamped to 1.0
        )
        assert breakdown.health_multiplier == 1.0

    def test_health_multiplier_appears_in_explanation(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.75,
        )
        assert "health_mult=0.75" in breakdown.explanation

    def test_existing_jitter_and_health_combine_correctly(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            jitter_penalty=0.05,
            health_multiplier=0.8,
        )
        # base = (raw_base - 0.05) * 0.8
        # Routing bonuses are added AFTER health multiply
        assert breakdown.health_multiplier == 0.8
        assert breakdown.jitter_penalty == 0.05
