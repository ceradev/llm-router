from __future__ import annotations

from packages.domain.gateway import GatewayTask, HealthState, ModelTier, Priority, ScoredCandidate
from packages.domain.models import Capability, ModelProfile

def _profile() -> ModelProfile:
    return ModelProfile(
        model_id="openai/gpt-4o",
        provider="openai",
        quality_score=5,
        latency_score=4,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        evaluation_status="verified",
    )

def test_gateway_task_has_discovery_mode_default_false() -> None:
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
    )
    assert task.discovery_mode is False

def test_scored_candidate_tier_defaults_to_tier2() -> None:
    candidate = ScoredCandidate(
        model=_profile(),
        priority_weight=100,
        db_model_id=1,
        rank=1,
        quality_score=5.0,
        latency_score=4.0,
        cost_score=3.0,
        final_score=0.9,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
    )
    assert candidate.tier == ModelTier.TIER2_PROVISIONAL
    assert candidate.health_status == HealthState.HEALTHY
    assert candidate.snapshot_latency_p50 is None

def test_gateway_task_has_max_cost_usd_default_none() -> None:
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
    )
    assert task.max_cost_usd is None

def test_model_tier_verified_enum_value() -> None:
    assert ModelTier.TIER1_VERIFIED.value == "tier1_verified"

def test_health_state_broken_enum_value() -> None:
    assert HealthState.BROKEN.value == "broken"
