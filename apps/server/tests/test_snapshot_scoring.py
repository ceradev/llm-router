from __future__ import annotations

import pytest
from datetime import datetime, timezone

from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotData
from packages.services.model_selection.snapshot_scoring import apply_snapshot_adjustments

def _profile(latency_score: int = 3, cost_score: int = 3) -> ModelProfile:
    return ModelProfile(
        model_id="openai/gpt-4o",
        provider="openai",
        quality_score=5,
        latency_score=latency_score,
        cost_score=cost_score,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        evaluation_status="verified",
    )

def _snapshot(**kwargs) -> SnapshotData:
    defaults = dict(
        model_id=1,
        p50_latency_ms=400.0,
        p95_latency_ms=900.0,
        avg_cost_per_1k_tokens=0.003,
        success_rate_7d=0.99,
        sample_size=200,
        recorded_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return SnapshotData(**defaults)

def test_no_snapshot_returns_raw_scores() -> None:
    profile = _profile(latency_score=4, cost_score=2)
    result = apply_snapshot_adjustments(profile=profile, snapshot=None)
    assert result.latency_score == pytest.approx(4.0)
    assert result.cost_score == pytest.approx(2.0)
    assert result.snapshot_used is False

def test_fast_model_gets_latency_boost() -> None:
    profile = _profile(latency_score=3)
    snap = _snapshot(p50_latency_ms=200.0)
    result = apply_snapshot_adjustments(profile=profile, snapshot=snap)
    assert result.latency_score > 3.0
    assert result.snapshot_used is True

def test_slow_model_gets_latency_penalty() -> None:
    profile = _profile(latency_score=3)
    snap = _snapshot(p50_latency_ms=3000.0)
    result = apply_snapshot_adjustments(profile=profile, snapshot=snap)
    assert result.latency_score < 3.0

def test_low_success_rate_triggers_reliability_penalty() -> None:
    profile = _profile()
    good_snap = _snapshot(success_rate_7d=0.99)
    bad_snap = _snapshot(success_rate_7d=0.70)
    good = apply_snapshot_adjustments(profile=profile, snapshot=good_snap)
    bad = apply_snapshot_adjustments(profile=profile, snapshot=bad_snap)
    assert bad.reliability_penalty > good.reliability_penalty

def test_scores_clamped_between_1_and_10() -> None:
    profile = _profile(latency_score=1)
    snap = _snapshot(p50_latency_ms=5000.0)
    result = apply_snapshot_adjustments(profile=profile, snapshot=snap)
    assert result.latency_score >= 1.0
    assert result.latency_score <= 10.0
