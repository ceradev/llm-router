from __future__ import annotations

from dataclasses import dataclass

from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotData


@dataclass(frozen=True)
class SnapshotAdjustedScores:
    latency_score: float
    cost_score: float
    reliability_penalty: float
    snapshot_used: bool

def _latency_bucket(p50_ms: float) -> float:
    if p50_ms < 300:
        return 0.5
    if p50_ms < 800:
        return 0.0
    if p50_ms < 2000:
        return -0.5
    return -1.0

def _cost_bucket(cost_per_1k: float) -> float:
    if cost_per_1k < 0.001:
        return 0.5
    if cost_per_1k < 0.005:
        return 0.0
    if cost_per_1k < 0.02:
        return -0.3
    return -0.7

def apply_snapshot_adjustments(
    *,
    profile: ModelProfile,
    snapshot: SnapshotData | None,
) -> SnapshotAdjustedScores:
    if snapshot is None:
        return SnapshotAdjustedScores(
            latency_score=float(profile.latency_score),
            cost_score=float(profile.cost_score),
            reliability_penalty=0.0,
            snapshot_used=False,
        )

    base_latency = float(profile.latency_score)
    base_cost = float(profile.cost_score)

    latency_delta = _latency_bucket(snapshot.p50_latency_ms) if snapshot.p50_latency_ms is not None else 0.0
    cost_delta = _cost_bucket(snapshot.avg_cost_per_1k_tokens) if snapshot.avg_cost_per_1k_tokens is not None else 0.0

    reliability_penalty = 0.0
    if snapshot.success_rate_7d is not None and snapshot.success_rate_7d < 0.90:
        reliability_penalty = (0.90 - snapshot.success_rate_7d) * (1.5 / 0.90)

    adjusted_latency = max(1.0, min(10.0, base_latency + latency_delta))
    adjusted_cost = max(1.0, min(10.0, base_cost + cost_delta))

    return SnapshotAdjustedScores(
        latency_score=adjusted_latency,
        cost_score=adjusted_cost,
        reliability_penalty=reliability_penalty,
        snapshot_used=True,
    )
