from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session, select

from packages.infrastructure.db.models.model_performance_snapshot import ModelPerformanceSnapshot


@dataclass(frozen=True)
class SnapshotData:
    model_id: int
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    avg_cost_per_1k_tokens: float | None
    success_rate_7d: float | None
    sample_size: int
    recorded_at: datetime


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest_snapshot(self, *, model_id: int) -> SnapshotData | None:
        stmt = (
            select(ModelPerformanceSnapshot)
            .where(ModelPerformanceSnapshot.model_id == model_id)
            .order_by(ModelPerformanceSnapshot.recorded_at.desc())
            .limit(1)
        )
        row = self.session.exec(stmt).first()
        if row is None:
            return None
        return SnapshotData(
            model_id=row.model_id,
            p50_latency_ms=row.p50_latency_ms,
            p95_latency_ms=row.p95_latency_ms,
            avg_cost_per_1k_tokens=row.avg_cost_per_1k_tokens,
            success_rate_7d=row.success_rate_7d,
            sample_size=row.sample_size,
            recorded_at=row.recorded_at,
        )

    def upsert_snapshot(
        self,
        *,
        model_id: int,
        p50_latency_ms: float | None,
        p95_latency_ms: float | None,
        avg_cost_per_1k_tokens: float | None,
        success_rate_7d: float | None,
        sample_size: int,
        snapshot_version: str = "v1",
    ) -> ModelPerformanceSnapshot:
        """Append a new snapshot row (history preserved; never mutates old rows)."""
        row = ModelPerformanceSnapshot(
            model_id=model_id,
            p50_latency_ms=p50_latency_ms,
            p95_latency_ms=p95_latency_ms,
            avg_cost_per_1k_tokens=avg_cost_per_1k_tokens,
            success_rate_7d=success_rate_7d,
            sample_size=sample_size,
            snapshot_version=snapshot_version,
            recorded_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_snapshot_model_ids(self) -> set[int]:
        """Return all model_ids that have at least one snapshot."""
        stmt = select(ModelPerformanceSnapshot.model_id).distinct()
        rows = self.session.exec(stmt).all()
        return {int(r) for r in rows}
