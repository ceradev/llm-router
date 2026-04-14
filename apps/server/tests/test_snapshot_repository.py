from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from packages.infrastructure.db.models.model_performance_snapshot import ModelPerformanceSnapshot
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    ModelPerformanceSnapshot.metadata.create_all(engine, tables=[ModelPerformanceSnapshot.__table__])
    with Session(engine) as s:
        yield s


def test_get_latest_snapshot_returns_none_when_empty(session: Session) -> None:
    repo = SnapshotRepository(session)
    assert repo.get_latest_snapshot(model_id=1) is None


def test_upsert_and_get_latest_snapshot(session: Session) -> None:
    repo = SnapshotRepository(session)
    repo.upsert_snapshot(
        model_id=42,
        p50_latency_ms=120.0,
        p95_latency_ms=350.0,
        avg_cost_per_1k_tokens=0.002,
        success_rate_7d=0.98,
        sample_size=500,
    )
    session.commit()

    result = repo.get_latest_snapshot(model_id=42)
    assert result is not None
    assert result.model_id == 42
    assert result.p50_latency_ms == pytest.approx(120.0)
    assert result.success_rate_7d == pytest.approx(0.98)


def test_get_latest_snapshot_returns_most_recent(session: Session) -> None:
    from datetime import datetime, timezone, timedelta

    repo = SnapshotRepository(session)
    old_row = ModelPerformanceSnapshot(
        model_id=1, p50_latency_ms=500.0, sample_size=10,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    session.add(old_row)
    session.flush()
    repo.upsert_snapshot(
        model_id=1, p50_latency_ms=200.0, p95_latency_ms=None,
        avg_cost_per_1k_tokens=None, success_rate_7d=None, sample_size=100,
    )
    session.commit()

    result = repo.get_latest_snapshot(model_id=1)
    assert result is not None
    assert result.p50_latency_ms == pytest.approx(200.0)


def test_list_snapshot_model_ids(session: Session) -> None:
    repo = SnapshotRepository(session)
    for mid in [1, 2, 2]:
        repo.upsert_snapshot(
            model_id=mid, p50_latency_ms=None, p95_latency_ms=None,
            avg_cost_per_1k_tokens=None, success_rate_7d=None, sample_size=0,
        )
    session.commit()
    ids = repo.list_snapshot_model_ids()
    assert ids == {1, 2}
