# Enterprise Routing Engine & Fast-Track — Implementation Plan

**Goal:** Implement Stability-First routing with Fast-Track for Verified models, dynamic intent-based scoring weights, multi-provider registry, circuit-breaker health tracking, and UI tier badges.

**Architecture:** Verified models skip real-time evaluation via cached performance snapshots stored in a new `model_performance_snapshots` table. A `model_health_status` table tracks consecutive failures for circuit-breaker logic. `ModelSelector` splits candidates into Tier 1 (verified) and Tier 2 (provisional) at query time. `ScoringEngine` adds `jitter_penalty` + per-intent weight tables. `FallbackExecutor` writes health events post-execution and marks models `broken`/`degraded`. The UI gains a `TierBadge` component and a `ProviderRouteTag` on `CategoryHighlightCard`.

**Design:** `thoughts/shared/designs/2026-04-14-enterprise-routing-engine-design.md`

---

## Dependency Graph

```
Batch 1 (parallel): 1.1, 1.2, 1.3          [DB schema + domain types — no deps]
Batch 2 (parallel): 2.1, 2.2, 2.3          [repositories + snapshot service — depends on batch 1]
Batch 3 (parallel): 3.1, 3.2, 3.3          [scoring + selector + executor v2 — depends on batch 2]
Batch 4 (parallel): 4.1, 4.2               [gateway wiring + UI components — depends on batch 3]
Batch 5 (serial):   5.1                    [Alembic migration — depends on batch 1 schemas]
```

---

## Batch 1: Foundation (parallel — 3 implementers)

All tasks have **no dependencies** and can run simultaneously.

---

### Task 1.1: Alembic Migration — `model_performance_snapshots` + `model_health_status`
**File:** `migrations/versions/c1a2b3d4e5f6_add_snapshots_and_health_status.py`
**Test:** none (DDL migration — verified by `alembic upgrade head` in CI)
**Depends:** none

> **Design requires:** snapshot-based scoring for Verified models + circuit-breaker health tracking.  
> **Implementation:** Two new tables with nullable FK to `llm_models.id`, index on `model_id` + `recorded_at` for snapshot lookup.

```python
"""Add model_performance_snapshots and model_health_status tables.

Revision ID: c1a2b3d4e5f6
Revises: f9a8b7c6d5e4
Create Date: 2026-04-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f9a8b7c6d5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- model_performance_snapshots ---
    op.create_table(
        "model_performance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("p50_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_cost_per_1k_tokens", sa.Float(), nullable=True),
        sa.Column("success_rate_7d", sa.Float(), nullable=True),     # 0.0–1.0
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_model_perf_snapshots_model_recorded",
        "model_performance_snapshots",
        ["model_id", "recorded_at"],
        unique=False,
    )

    # --- model_health_status ---
    op.create_table(
        "model_health_status",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "model_id",
            sa.Integer(),
            sa.ForeignKey("llm_models.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,   # one active health row per model
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="healthy",
        ),  # healthy | degraded | broken
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("model_health_status")
    op.drop_index("ix_model_perf_snapshots_model_recorded", table_name="model_performance_snapshots")
    op.drop_table("model_performance_snapshots")
```

**Verify:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
**Commit:** `feat(db): add model_performance_snapshots and model_health_status tables`

---

### Task 1.2: ORM Models — `ModelPerformanceSnapshot` + `ModelHealthStatus`
**File:** `packages/infrastructure/db/models/model_performance_snapshot.py`
**File B:** `packages/infrastructure/db/models/model_health_status.py`
**Test:** none (pure ORM declarations — exercised by repo tests in batch 2)
**Depends:** none

> **Design requires:** snapshot-based scoring + health circuit-breaker.  
> **Implementation:** Follow existing `TimestampMixin + Base` pattern from `llm_model.py`. Two separate files, registered in `__init__.py`.

**`model_performance_snapshot.py`:**
```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlmodel import Field

from packages.infrastructure.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class ModelPerformanceSnapshot(Base, table=True):
    """Pre-calculated performance metrics for Verified models (Fast-Track lane)."""

    __tablename__ = "model_performance_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        sa_column=Column(Integer(), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    p50_latency_ms: float | None = Field(default=None)
    p95_latency_ms: float | None = Field(default=None)
    avg_cost_per_1k_tokens: float | None = Field(default=None)
    success_rate_7d: float | None = Field(default=None)   # 0.0–1.0
    sample_size: int = Field(default=0)
    snapshot_version: str = Field(default="v1", max_length=32)
    recorded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
```

**`model_health_status.py`:**
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, Text, func
from sqlmodel import Field

from packages.infrastructure.db.base import Base


class ModelHealthStatus(Base, table=True):
    """Circuit-breaker health state per model. One row per model (upserted)."""

    __tablename__ = "model_health_status"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        sa_column=Column(Integer(), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
    )
    # healthy | degraded | broken
    status: str = Field(default="healthy", max_length=32)
    consecutive_failures: int = Field(default=0)
    last_failure_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_success_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failure_reason: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
```

**Register in `packages/infrastructure/db/models/__init__.py`** — add these two imports and export names to `__all__`.

**Verify:** `python -c "from packages.infrastructure.db.models import ModelPerformanceSnapshot, ModelHealthStatus; print('ok')"`
**Commit:** `feat(db): add ModelPerformanceSnapshot and ModelHealthStatus ORM models`

---

### Task 1.3: Domain — `ModelTier` enum + `HealthState` + extend `ScoredCandidate`
**File:** `packages/domain/gateway.py` (modify existing)
**Test:** `apps/server/tests/test_domain_gateway_types.py` (new)
**Depends:** none

> **Design requires:** Tier 1 / Tier 2 classification and health circuit-breaker states.  
> **Implementation:** Add `ModelTier` + `HealthState` enums. Extend `ScoredCandidate` with `tier`, `health_status`, and `snapshot_latency_p50`. Add `DiscoveryMode` flag to `GatewayTask`.

```python
# Additions to packages/domain/gateway.py
# (insert after existing enums, before GatewayTask)

class ModelTier(str, Enum):
    """Routing tier derived from evaluation_status."""
    TIER1_VERIFIED = "tier1_verified"      # Fast-Track: uses snapshot scoring
    TIER2_PROVISIONAL = "tier2_provisional"  # Standard: full evaluation scoring


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
```

Extend `GatewayTask` — add field:
```python
discovery_mode: bool = False  # unlocks Tier 2 even when Tier 1 available
```

Extend `ScoredCandidate` — add fields:
```python
tier: ModelTier = ModelTier.TIER2_PROVISIONAL
health_status: HealthState = HealthState.HEALTHY
snapshot_latency_p50: float | None = None  # ms, from latest snapshot
```

**Test file `apps/server/tests/test_domain_gateway_types.py`:**
```python
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


def test_model_tier_verified_enum_value() -> None:
    assert ModelTier.TIER1_VERIFIED.value == "tier1_verified"


def test_health_state_broken_enum_value() -> None:
    assert HealthState.BROKEN.value == "broken"
```

**Verify:** `pytest apps/server/tests/test_domain_gateway_types.py -v`
**Commit:** `feat(domain): add ModelTier, HealthState enums and extend ScoredCandidate`

---

## Batch 2: Repositories (parallel — 3 implementers)

All tasks depend on **Batch 1** (ORM models + domain types).

---

### Task 2.1: `SnapshotRepository` — read/write performance snapshots
**File:** `packages/infrastructure/db/repositories/snapshot_repository.py`
**Test:** `apps/server/tests/test_snapshot_repository.py`
**Depends:** 1.1, 1.2

> **Design requires:** Verified models use pre-calculated scores via snapshots.  
> **Implementation:** `get_latest_snapshot(model_id)` → most recent row by `recorded_at`. `upsert_snapshot(...)` → insert new row (append-only, never update in place, so history is preserved). `list_snapshot_model_ids()` → set of model IDs with ≥1 snapshot.

```python
# packages/infrastructure/db/repositories/snapshot_repository.py
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
```

**Test `apps/server/tests/test_snapshot_repository.py`:**
```python
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from packages.infrastructure.db.models.model_performance_snapshot import ModelPerformanceSnapshot
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
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
```

**Verify:** `pytest apps/server/tests/test_snapshot_repository.py -v`
**Commit:** `feat(db): add SnapshotRepository for model performance snapshots`

---

### Task 2.2: `HealthRepository` — circuit-breaker state read/write
**File:** `packages/infrastructure/db/repositories/health_repository.py`
**Test:** `apps/server/tests/test_health_repository.py`
**Depends:** 1.1, 1.2

> **Design requires:** Circuit breaker — auto status change to `broken`/`degraded` after X consecutive failures.  
> **Implementation:** `DEGRADED_THRESHOLD = 3`, `BROKEN_THRESHOLD = 6`. `record_success(model_id)` resets to healthy. `record_failure(model_id, reason)` increments and transitions state. `get_broken_model_ids()` → set for selector to exclude.

```python
# packages/infrastructure/db/repositories/health_repository.py
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from packages.infrastructure.db.models.model_health_status import ModelHealthStatus
from packages.domain.gateway import HealthState

_DEGRADED_THRESHOLD: int = 3
_BROKEN_THRESHOLD: int = 6


class HealthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_or_create(self, model_id: int) -> ModelHealthStatus:
        stmt = select(ModelHealthStatus).where(ModelHealthStatus.model_id == model_id)
        row = self.session.exec(stmt).first()
        if row is None:
            row = ModelHealthStatus(model_id=model_id, status=HealthState.HEALTHY.value)
            self.session.add(row)
            self.session.flush()
        return row

    def record_success(self, *, model_id: int) -> None:
        row = self._get_or_create(model_id)
        row.consecutive_failures = 0
        row.status = HealthState.HEALTHY.value
        row.last_success_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        self.session.add(row)

    def record_failure(self, *, model_id: int, reason: str) -> HealthState:
        """Record a failure and return the resulting HealthState."""
        row = self._get_or_create(model_id)
        row.consecutive_failures += 1
        row.last_failure_at = datetime.now(timezone.utc)
        row.failure_reason = reason[:512]
        row.updated_at = datetime.now(timezone.utc)

        if row.consecutive_failures >= _BROKEN_THRESHOLD:
            row.status = HealthState.BROKEN.value
        elif row.consecutive_failures >= _DEGRADED_THRESHOLD:
            row.status = HealthState.DEGRADED.value

        self.session.add(row)
        return HealthState(row.status)

    def get_status(self, *, model_id: int) -> HealthState:
        stmt = select(ModelHealthStatus).where(ModelHealthStatus.model_id == model_id)
        row = self.session.exec(stmt).first()
        if row is None:
            return HealthState.HEALTHY
        return HealthState(row.status)

    def get_broken_model_ids(self) -> set[int]:
        """Model IDs in BROKEN state — selector must exclude these."""
        stmt = select(ModelHealthStatus.model_id).where(
            ModelHealthStatus.status == HealthState.BROKEN.value
        )
        rows = self.session.exec(stmt).all()
        return {int(r) for r in rows}

    def get_degraded_model_ids(self) -> set[int]:
        stmt = select(ModelHealthStatus.model_id).where(
            ModelHealthStatus.status == HealthState.DEGRADED.value
        )
        rows = self.session.exec(stmt).all()
        return {int(r) for r in rows}
```

**Test `apps/server/tests/test_health_repository.py`:**
```python
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from packages.infrastructure.db.models.model_health_status import ModelHealthStatus
from packages.infrastructure.db.repositories.health_repository import HealthRepository, _BROKEN_THRESHOLD, _DEGRADED_THRESHOLD
from packages.domain.gateway import HealthState


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_initial_status_is_healthy(session: Session) -> None:
    repo = HealthRepository(session)
    assert repo.get_status(model_id=1) == HealthState.HEALTHY


def test_record_success_resets_to_healthy(session: Session) -> None:
    repo = HealthRepository(session)
    for _ in range(_DEGRADED_THRESHOLD):
        repo.record_failure(model_id=5, reason="timeout")
    session.commit()
    assert repo.get_status(model_id=5) == HealthState.DEGRADED

    repo.record_success(model_id=5)
    session.commit()
    assert repo.get_status(model_id=5) == HealthState.HEALTHY


def test_transitions_to_degraded_at_threshold(session: Session) -> None:
    repo = HealthRepository(session)
    for i in range(_DEGRADED_THRESHOLD):
        state = repo.record_failure(model_id=10, reason="err")
    session.commit()
    assert state == HealthState.DEGRADED


def test_transitions_to_broken_at_threshold(session: Session) -> None:
    repo = HealthRepository(session)
    final_state = HealthState.HEALTHY
    for _ in range(_BROKEN_THRESHOLD):
        final_state = repo.record_failure(model_id=20, reason="err")
    session.commit()
    assert final_state == HealthState.BROKEN


def test_get_broken_model_ids(session: Session) -> None:
    repo = HealthRepository(session)
    for _ in range(_BROKEN_THRESHOLD):
        repo.record_failure(model_id=99, reason="down")
    session.commit()
    broken = repo.get_broken_model_ids()
    assert 99 in broken
    assert 1 not in broken
```

**Verify:** `pytest apps/server/tests/test_health_repository.py -v`
**Commit:** `feat(db): add HealthRepository with circuit-breaker thresholds`

---

### Task 2.3: `SnapshotScoringService` — adjust latency/cost scores using snapshot data
**File:** `packages/services/model_selection/snapshot_scoring.py`
**Test:** `apps/server/tests/test_snapshot_scoring.py`
**Depends:** 2.1 (imports `SnapshotData`)

> **Design requires:** Verified models use pre-calculated scores adjusted by real-time latency/cost metrics.  
> **Implementation:** Pure function `apply_snapshot_adjustments(profile, snapshot)` → returns adjusted `(latency_score, cost_score)` as floats, clamped 1–5. Latency score is adjusted based on p50_latency_ms bucket; cost score nudged by avg_cost_per_1k_tokens bucket. `success_rate_7d < 0.90` applies a reliability penalty of -0.5.

```python
# packages/services/model_selection/snapshot_scoring.py
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
    """Map p50 latency to score delta relative to baseline score of 3.0."""
    if p50_ms < 300:
        return 0.5
    if p50_ms < 800:
        return 0.0
    if p50_ms < 2000:
        return -0.5
    return -1.0


def _cost_bucket(cost_per_1k: float) -> float:
    """Map avg cost/1k tokens to score delta."""
    if cost_per_1k < 0.001:   # e.g. Groq free tier
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
    """
    Returns adjusted latency/cost scores for a Verified model using snapshot data.
    Falls back to raw profile scores when no snapshot is available.
    """
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
        # Linear penalty: 0.5 at 90%, up to 1.5 at 0%
        reliability_penalty = (0.90 - snapshot.success_rate_7d) * (1.5 / 0.90)

    adjusted_latency = max(1.0, min(5.0, base_latency + latency_delta))
    adjusted_cost = max(1.0, min(5.0, base_cost + cost_delta))

    return SnapshotAdjustedScores(
        latency_score=adjusted_latency,
        cost_score=adjusted_cost,
        reliability_penalty=reliability_penalty,
        snapshot_used=True,
    )
```

**Test `apps/server/tests/test_snapshot_scoring.py`:**
```python
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


def test_scores_clamped_between_1_and_5() -> None:
    profile = _profile(latency_score=1)
    snap = _snapshot(p50_latency_ms=5000.0)  # big penalty
    result = apply_snapshot_adjustments(profile=profile, snapshot=snap)
    assert result.latency_score >= 1.0
```

**Verify:** `pytest apps/server/tests/test_snapshot_scoring.py -v`
**Commit:** `feat(scoring): add SnapshotScoringService for Fast-Track latency/cost adjustment`

---

## Batch 3: Core Engine v2 (parallel — 3 implementers)

All tasks depend on **Batch 2**.

---

### Task 3.1: `ScoringEngine` v2 — intent-based dynamic weights + jitter penalty
**File:** `packages/core/scoring/engine.py` (modify existing)
**Test:** `apps/server/tests/test_scoring_engine_v2.py` (new, separate from existing test)
**Depends:** 2.3 (imports `SnapshotAdjustedScores`)

> **Design requires:** Dynamic weighting (Intent-based) + Jitter/Reliability penalties.  
> **Implementation:** Add `_weights_for_intent(intent)` table. Add `jitter_penalty` param. Extend `compute_model_score` signature with `intent: Intent | None = None` and `jitter_penalty: float = 0.0`. Existing signature is fully backward-compatible. `jitter_penalty` is subtracted from `base_total` before routing bonuses.

**Changes to `packages/core/scoring/engine.py`:**

Add after the imports:
```python
from packages.domain.gateway import Intent, Priority
```

Add new function `_weights_for_intent` (returns `tuple[float, float, float]`):
```python
def _weights_for_intent(intent: Intent) -> tuple[float, float, float]:
    """Per-intent weight overrides applied BEFORE priority weights."""
    if intent == Intent.CODE:
        # Code: quality >> latency > cost
        return (1.15, 0.85, 0.70)
    if intent == Intent.ANALYSIS:
        # Analysis: quality dominant, cost secondary
        return (1.10, 0.80, 0.90)
    if intent == Intent.CREATIVE:
        # Creative: quality first, latency less critical
        return (1.20, 0.70, 0.80)
    # GENERAL: balanced — no override
    return (1.0, 1.0, 1.0)
```

Extend `compute_model_score` signature with two new keyword-only params:
```python
def compute_model_score(
    *,
    model: ModelProfile,
    priority: Priority,
    priority_weight: int,
    complexity_score: float | None = None,
    requires_code: bool = False,
    requires_reasoning: bool = False,
    requires_tools: bool = False,
    use_cases: list[str] | None = None,
    preferred_providers: list[str] | None = None,
    avg_rating: float | None = None,
    ratings_count: int = 0,
    # NEW v2 params:
    intent: Intent | None = None,
    jitter_penalty: float = 0.0,
) -> ScoreBreakdown:
```

Inside `compute_model_score`, after `_weights_for_priority` call, add:
```python
    # v2: apply intent-based multipliers on top of priority weights
    if intent is not None:
        iq, il, ic = _weights_for_intent(intent)
        quality_weight *= iq
        latency_weight *= il
        cost_weight *= ic
        quality_weight, latency_weight, cost_weight = _renormalize_weights(
            quality_weight, latency_weight, cost_weight
        )
```

After `base_total` calculation, add:
```python
    # v2: subtract jitter/reliability penalty from snapshot (0.0 if no snapshot)
    base_total = max(0.0, base_total - jitter_penalty)
```

Also extend `ScoreBreakdown` with:
```python
jitter_penalty: float = 0.0  # field added to dataclass
```

Update explanation string to include `jitter_penalty={jitter_penalty:.3f}`.

**Test `apps/server/tests/test_scoring_engine_v2.py`:**
```python
from __future__ import annotations

import pytest

from packages.core.scoring.engine import compute_model_score
from packages.domain.gateway import Intent, Priority
from packages.domain.models import Capability, ModelProfile


def _profile(**kw) -> ModelProfile:
    defaults = dict(
        model_id="p/m",
        provider="p",
        quality_score=3,
        latency_score=3,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )
    defaults.update(kw)
    return ModelProfile(**defaults)  # type: ignore[arg-type]


def test_code_intent_boosts_quality_weight() -> None:
    model = _profile(quality_score=5, latency_score=2)
    with_intent = compute_model_score(
        model=model, priority=Priority.BALANCED, priority_weight=100, intent=Intent.CODE
    ).total
    without_intent = compute_model_score(
        model=model, priority=Priority.BALANCED, priority_weight=100
    ).total
    # Higher quality weight means high-quality model scores better under CODE intent
    assert with_intent > without_intent


def test_jitter_penalty_reduces_score() -> None:
    model = _profile()
    base = compute_model_score(model=model, priority=Priority.BALANCED, priority_weight=100).total
    penalized = compute_model_score(
        model=model, priority=Priority.BALANCED, priority_weight=100, jitter_penalty=0.3
    ).total
    assert penalized < base


def test_jitter_penalty_does_not_go_negative() -> None:
    model = _profile(quality_score=1, latency_score=1, cost_score=1)
    result = compute_model_score(
        model=model, priority=Priority.BALANCED, priority_weight=0, jitter_penalty=999.0
    )
    assert result.total >= 0.0


def test_intent_none_is_backward_compatible() -> None:
    model = _profile()
    with_none = compute_model_score(model=model, priority=Priority.BALANCED, priority_weight=100, intent=None).total
    without = compute_model_score(model=model, priority=Priority.BALANCED, priority_weight=100).total
    assert with_none == pytest.approx(without)


def test_creative_intent_penalizes_latency_sensitive_ranking() -> None:
    fast_cheap = _profile(model_id="m/fast", latency_score=5, cost_score=5, quality_score=2)
    quality = _profile(model_id="m/quality", latency_score=2, cost_score=2, quality_score=5)
    kw = dict(priority=Priority.BALANCED, priority_weight=100, intent=Intent.CREATIVE)
    assert compute_model_score(model=quality, **kw).total > compute_model_score(model=fast_cheap, **kw).total
```

**Verify:** `pytest apps/server/tests/test_scoring_engine_v2.py -v`
**Commit:** `feat(scoring): add intent-based dynamic weights and jitter_penalty to ScoringEngine`

---

### Task 3.2: `ModelSelector` v2 — tiered filtering + Fast-Track lane
**File:** `packages/services/model_selection/service.py` (modify existing)
**Test:** `apps/server/tests/test_model_selector_v2.py` (new)
**Depends:** 2.1, 2.2, 2.3, 3.1

> **Design requires:** Prioritize Verified models unless in Discovery Mode. Fast-Track uses snapshot scores.  
> **Implementation:** `ModelSelector.__init__` gains optional `snapshot_repo` + `health_repo`. `_load_candidates` splits into Tier 1 (verified, not broken) and Tier 2 (provisional). In non-discovery mode, if Tier 1 non-empty → use only Tier 1. `_rank_candidates` calls `apply_snapshot_adjustments` for verified models and passes `jitter_penalty` from snapshot reliability to `compute_model_score`. Discovery mode unlocks Tier 2.

**Changes to `packages/services/model_selection/service.py`:**

```python
# New imports at top:
from packages.domain.gateway import HealthState, ModelTier
from packages.services.model_selection.snapshot_scoring import apply_snapshot_adjustments
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.infrastructure.db.repositories.health_repository import HealthRepository

# Modified __init__:
class ModelSelector:
    def __init__(
        self,
        *,
        model_repository: ModelRepository,
        snapshot_repository: SnapshotRepository | None = None,
        health_repository: HealthRepository | None = None,
    ) -> None:
        self.model_repository = model_repository
        self.snapshot_repository = snapshot_repository
        self.health_repository = health_repository
```

Modify `build_decision` to pass `task.discovery_mode` through to `_load_candidates`.

Modify `_load_candidates` to:
1. Call `health_repository.get_broken_model_ids()` (if repo available)
2. Filter out broken model IDs from `db_rows`
3. Split remaining rows into `tier1` (evaluation_status == "verified") and `tier2` (provisional)
4. If not discovery_mode AND tier1 non-empty → use only tier1 rows
5. Otherwise use all (tier1 + tier2)
6. Annotate `ModelRoutingRow` tier (add a thin wrapper or return tuple with tier flag)

Modify `_rank_candidates` to:
1. Fetch snapshot for each verified model via `snapshot_repository.get_latest_snapshot(model_id=row.db_model_id)`
2. Call `apply_snapshot_adjustments(profile=row.model, snapshot=snap)`
3. Build an adjusted `ModelProfile` (dataclass replace with adjusted latency/cost scores)
4. Pass `jitter_penalty=adjusted.reliability_penalty` to `compute_model_score`
5. Pass `intent=intent_from_evaluation_string(evaluation.intent)` (already resolved by orchestrator)
6. Set `ScoredCandidate.tier` and `ScoredCandidate.health_status` and `ScoredCandidate.snapshot_latency_p50`

> Note: `dataclasses.replace(row.model, latency_score=round(adjusted.latency_score), cost_score=round(adjusted.cost_score))` for the adjusted profile. Scores stay as `int` in `ModelProfile`; `apply_snapshot_adjustments` returns `float` — round to nearest int before replace.

**Test `apps/server/tests/test_model_selector_v2.py`:**
```python
from __future__ import annotations

import pytest

from packages.domain.gateway import GatewayTask, Intent, ModelTier, Priority
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation.types import PromptEvaluationResult


def _eval(**kw) -> PromptEvaluationResult:
    defaults = dict(
        intent="general",
        complexity_score=0.5,
        requires_code=False,
        requires_reasoning=False,
        requires_tools=False,
    )
    defaults.update(kw)
    return PromptEvaluationResult(**defaults)  # type: ignore[arg-type]


def _task(**kw) -> GatewayTask:
    defaults = dict(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
    )
    defaults.update(kw)
    return GatewayTask(**defaults)  # type: ignore[arg-type]


def _profile(model_id: str, status: str = "verified") -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=4,
        latency_score=4,
        cost_score=4,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        evaluation_status=status,
    )


class _StubRepo:
    """Minimal stub ModelRepository returning preset rows."""

    def __init__(self, rows: list[ModelRoutingRow]) -> None:
        self._rows = rows
        self.session = None

    def list_routing_candidates(self, **_) -> list[ModelRoutingRow]:
        return self._rows


def _row(model_id: str, status: str = "verified", db_id: int = 1) -> ModelRoutingRow:
    return ModelRoutingRow(
        model=_profile(model_id, status),
        priority_weight=100,
        db_model_id=db_id,
    )


def test_tier1_only_used_when_verified_models_exist() -> None:
    rows = [_row("m/verified", "verified", 1), _row("m/provisional", "provisional", 2)]
    repo = _StubRepo(rows)
    selector = ModelSelector(model_repository=repo)  # type: ignore[arg-type]
    decision = selector.build_decision(task=_task(), intent=Intent.GENERAL, evaluation=_eval())
    # Only verified model should appear as top candidate
    candidate_ids = [c.model_id for c in decision.candidates]
    assert "m/verified" in candidate_ids
    # provisional should be excluded in non-discovery mode
    assert "m/provisional" not in candidate_ids


def test_discovery_mode_includes_tier2() -> None:
    rows = [_row("m/verified", "verified", 1), _row("m/provisional", "provisional", 2)]
    repo = _StubRepo(rows)
    selector = ModelSelector(model_repository=repo)  # type: ignore[arg-type]
    decision = selector.build_decision(
        task=_task(discovery_mode=True),
        intent=Intent.GENERAL,
        evaluation=_eval(),
    )
    candidate_ids = [c.model_id for c in decision.candidates]
    assert "m/verified" in candidate_ids
    assert "m/provisional" in candidate_ids


def test_falls_back_to_tier2_when_no_verified() -> None:
    rows = [_row("m/provisional", "provisional", 1)]
    repo = _StubRepo(rows)
    selector = ModelSelector(model_repository=repo)  # type: ignore[arg-type]
    decision = selector.build_decision(task=_task(), intent=Intent.GENERAL, evaluation=_eval())
    assert decision.candidates


def test_scored_candidate_has_tier_annotation() -> None:
    rows = [_row("m/verified", "verified", 1)]
    repo = _StubRepo(rows)
    selector = ModelSelector(model_repository=repo)  # type: ignore[arg-type]
    decision = selector.build_decision(task=_task(), intent=Intent.GENERAL, evaluation=_eval())
    assert decision.scored_candidates[0].tier == ModelTier.TIER1_VERIFIED
```

**Verify:** `pytest apps/server/tests/test_model_selector_v2.py -v`
**Commit:** `feat(selector): implement tiered Fast-Track selection with snapshot scoring`

---

### Task 3.3: `FallbackExecutor` v2 — health event recording + cross-provider fallback
**File:** `packages/services/execution/fallback_executor.py` (modify existing)
**Test:** `apps/server/tests/test_fallback_executor_v2.py` (new)
**Depends:** 2.2 (imports `HealthRepository`)

> **Design requires:** FallbackExecutor marks models as `broken` in DB upon failure. Cross-provider failover.  
> **Implementation:** `FallbackExecutor.__init__` gains optional `health_repository`. After success → `health_repo.record_success(model_id=db_model_id)`. After failure → `health_repo.record_failure(...)`. `db_model_id` must come from `ScoredCandidate` lookup — add `_db_id_for_model(model_id, scored_candidates)` helper. Provider resolution: try `self.providers.get(model.provider)` first, then `self.providers.get("openrouter")` as existing fallback. Add `prefer_direct: bool = True` flag — when True, skip `openrouter` if direct provider available.

**New `__init__` signature:**
```python
class FallbackExecutor:
    def __init__(
        self,
        providers: dict[str, ProviderAdapter],
        *,
        max_total_attempts: int = 8,
        max_failures_per_model: int = 1,
        health_repository: HealthRepository | None = None,
        prefer_direct: bool = True,
    ) -> None:
        self.providers = providers
        self.max_total_attempts = max(1, int(max_total_attempts))
        self.max_failures_per_model = max(1, int(max_failures_per_model))
        self.health_repository = health_repository
        self.prefer_direct = prefer_direct
```

Add to `run()`, after success block:
```python
if self.health_repository is not None:
    db_id = _db_id_for_model(model.model_id, decision.scored_candidates)
    if db_id is not None:
        self.health_repository.record_success(model_id=db_id)
```

Add to `run()`, after failure block:
```python
if self.health_repository is not None:
    db_id = _db_id_for_model(model.model_id, decision.scored_candidates)
    if db_id is not None:
        self.health_repository.record_failure(model_id=db_id, reason=str(exc))
```

Add helper:
```python
def _db_id_for_model(model_id: str, scored: tuple[ScoredCandidate, ...]) -> int | None:
    for sc in scored:
        if sc.model.model_id == model_id:
            return sc.db_model_id
    return None
```

**Test `apps/server/tests/test_fallback_executor_v2.py`:**
```python
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from packages.domain.gateway import (
    HealthState, ModelTier, Priority, RoutedRequest, RoutingDecision, ScoredCandidate, Intent,
)
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.providers.base import ProviderAdapter, ProviderError
from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.services.execution.fallback_executor import FallbackExecutor


def _profile(model_id: str, provider: str = "openai") -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider=provider,
        quality_score=4,
        latency_score=4,
        cost_score=4,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )


def _scored(model: ModelProfile, db_id: int = 1) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=100,
        db_model_id=db_id,
        rank=1,
        quality_score=4.0,
        latency_score=4.0,
        cost_score=4.0,
        final_score=0.8,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER1_VERIFIED,
    )


def _request() -> RoutedRequest:
    return RoutedRequest(
        prompt="hello",
        temperature=0.2,
        max_tokens=None,
        require_json=False,
    )


def _decision(candidates: list[ModelProfile], scored: tuple[ScoredCandidate, ...]) -> RoutingDecision:
    return RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.2,
        candidates=candidates,
        scored_candidates=scored,
    )


def test_health_repo_records_success_on_ok_response() -> None:
    model = _profile("openai/gpt-4o")
    mock_provider = MagicMock(spec=ProviderAdapter)
    mock_provider.generate.return_value = MagicMock(
        content="hi", provider="openai", model_id="openai/gpt-4o",
        latency_ms=100, input_tokens=10, output_tokens=20, cost=0.001,
    )
    health_repo = MagicMock()
    executor = FallbackExecutor(
        {"openai": mock_provider},
        health_repository=health_repo,
    )
    scored = _scored(model, db_id=42)
    decision = _decision([model], (scored,))
    executor.run(request=_request(), decision=decision)
    health_repo.record_success.assert_called_once_with(model_id=42)


def test_health_repo_records_failure_on_provider_error() -> None:
    model = _profile("openai/gpt-4o")
    mock_provider = MagicMock(spec=ProviderAdapter)
    mock_provider.generate.side_effect = ProviderError("timeout")
    health_repo = MagicMock()
    executor = FallbackExecutor(
        {"openai": mock_provider},
        health_repository=health_repo,
    )
    scored = _scored(model, db_id=7)
    decision = _decision([model], (scored,))
    with pytest.raises(Exception):
        executor.run(request=_request(), decision=decision)
    health_repo.record_failure.assert_called_once_with(model_id=7, reason="timeout")
```

**Verify:** `pytest apps/server/tests/test_fallback_executor_v2.py -v`
**Commit:** `feat(executor): add health event recording and prefer_direct provider strategy`

---

## Batch 4: Integration & UI (parallel — 2 implementers)

Both tasks depend on **Batch 3**.

---

### Task 4.1: `ProviderRegistry` v2 — real HTTP clients per provider
**File:** `packages/infrastructure/providers/registry.py` (modify existing)
**Test:** `apps/server/tests/test_provider_registry_v2.py` (new)
**Depends:** 3.3 (wired into executor's `prefer_direct`)

> **Design requires:** Multi-provider registry — direct OpenAI, Anthropic, Groq connections, OpenRouter as aggregator fallback.  
> **Implementation:** `build_provider_clients(settings)` reads API keys from `get_settings()`. If key present → build real `HttpProviderClient`; else → `DemoProviderClient` (existing). Keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`. `HttpProviderClient` wraps HTTPX with appropriate base URLs and auth headers. Add `HttpProviderClient` as new file; registry imports it.

**New file `packages/infrastructure/providers/http_provider_client.py`:**
```python
from __future__ import annotations

import httpx

from packages.domain.gateway import RoutedRequest
from packages.domain.models import ModelProfile
from packages.infrastructure.providers.base import ProviderAdapter, ProviderError, ProviderResponse


_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

_PROVIDER_AUTH_HEADERS: dict[str, str] = {
    "anthropic": "x-api-key",
}


class HttpProviderClient(ProviderAdapter):
    """Real HTTPX-backed provider client (OpenAI-compatible chat completions)."""

    def __init__(self, provider: str, api_key: str, *, timeout_s: float = 30.0) -> None:
        self.provider = provider
        self._api_key = api_key
        self._base_url = _PROVIDER_BASE_URLS.get(provider, "https://openrouter.ai/api/v1")
        self._timeout = timeout_s
        auth_header = _PROVIDER_AUTH_HEADERS.get(provider, "Authorization")
        auth_value = api_key if provider == "anthropic" else f"Bearer {api_key}"
        self._headers = {
            auth_header: auth_value,
            "Content-Type": "application/json",
        }

    def generate(self, request: RoutedRequest, model: ModelProfile) -> ProviderResponse:
        import time
        payload = {
            "model": model.model_id.split("/", 1)[-1] if "/" in model.model_id else model.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.require_json:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        try:
            with httpx.Client(base_url=self._base_url, headers=self._headers, timeout=self._timeout) as client:
                resp = client.post("/chat/completions", json=payload)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"{self.provider} HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"{self.provider} network error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ProviderResponse(
            content=content,
            provider=self.provider,
            model_id=model.model_id,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=elapsed_ms,
            cost=0.0,  # cost calc in separate service
        )
```

**Updated `packages/infrastructure/providers/registry.py`:**
```python
from __future__ import annotations

from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.providers.config.anthropic import PROVIDER_NAME as ANTHROPIC_PROVIDER
from packages.infrastructure.providers.config.deepseek import PROVIDER_NAME as DEEPSEEK_PROVIDER
from packages.infrastructure.providers.config.groq import PROVIDER_NAME as GROQ_PROVIDER
from packages.infrastructure.providers.config.openai import PROVIDER_NAME as OPENAI_PROVIDER
from packages.infrastructure.providers.config.openrouter import PROVIDER_NAME as OPENROUTER_PROVIDER
from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.infrastructure.providers.http_provider_client import HttpProviderClient
from packages.infrastructure.providers.base import ProviderAdapter


def build_provider_clients() -> dict[str, ProviderAdapter]:
    """
    Build provider map. Direct provider (HttpProviderClient) when API key present;
    DemoProviderClient otherwise (safe default for local dev without keys).
    """
    settings = get_settings()

    def _client(provider: str, key_attr: str) -> ProviderAdapter:
        key = getattr(settings, key_attr, None)
        if key:
            return HttpProviderClient(provider, key)
        return DemoProviderClient(provider)

    return {
        OPENAI_PROVIDER: _client(OPENAI_PROVIDER, "openai_api_key"),
        ANTHROPIC_PROVIDER: _client(ANTHROPIC_PROVIDER, "anthropic_api_key"),
        GROQ_PROVIDER: _client(GROQ_PROVIDER, "groq_api_key"),
        DEEPSEEK_PROVIDER: _client(DEEPSEEK_PROVIDER, "deepseek_api_key"),
        OPENROUTER_PROVIDER: _client(OPENROUTER_PROVIDER, "openrouter_api_key"),
    }
```

**Test `apps/server/tests/test_provider_registry_v2.py`:**
```python
from __future__ import annotations

from unittest.mock import patch

from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.infrastructure.providers.http_provider_client import HttpProviderClient
from packages.infrastructure.providers.registry import build_provider_clients


def test_returns_demo_clients_when_no_keys(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    clients = build_provider_clients()
    assert all(isinstance(c, DemoProviderClient) for c in clients.values())


def test_returns_http_client_when_key_present(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    clients = build_provider_clients()
    assert isinstance(clients["openai"], HttpProviderClient)


def test_all_expected_providers_registered() -> None:
    clients = build_provider_clients()
    assert {"openai", "anthropic", "groq", "deepseek", "openrouter"}.issubset(clients.keys())
```

**Verify:** `pytest apps/server/tests/test_provider_registry_v2.py -v`
**Commit:** `feat(providers): implement HttpProviderClient and multi-provider registry v2`

---

### Task 4.2: UI — `TierBadge` component + `ModelDecision.tier` propagation in `CategoryHighlightCard`
**File:** `apps/web/src/features/results/components/TierBadge.tsx` (new)
**File B:** `apps/web/src/features/results/components/CategoryHighlightCard.tsx` (modify)
**File C:** `apps/web/src/features/results/types.ts` (modify — add `tier` + `healthStatus` fields)
**Test:** none (UI component — verified by `bun run build` passing)
**Depends:** 3.2 (backend sends `tier` + `health_status` in scored candidates)

> **Design requires:** UI remains intuitive while providing data-driven alternatives.  
> **Implementation:** Add `tier` and `healthStatus` to `ModelDecision` type. `TierBadge` renders a small pill: green shield for `tier1_verified`, grey for `tier2_provisional`. `CategoryHighlightCard` shows `TierBadge` next to model name. Follows existing Tailwind + Framer Motion conventions from `CategoryHighlightCard.tsx`.

**New `apps/web/src/features/results/components/TierBadge.tsx`:**
```tsx
import { motion } from "framer-motion"

type TierBadgeProps = {
  tier: string | undefined
  className?: string
}

const TIER_CONFIGS: Record<string, { label: string; className: string }> = {
  tier1_verified: {
    label: "Verified",
    className:
      "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  },
  tier2_provisional: {
    label: "Provisional",
    className:
      "bg-slate-500/10 text-slate-400 border border-slate-500/20",
  },
}

export function TierBadge({ tier, className = "" }: Readonly<TierBadgeProps>) {
  if (!tier) return null
  const config = TIER_CONFIGS[tier]
  if (!config) return null

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${config.className} ${className}`}
    >
      {tier === "tier1_verified" ? (
        <svg
          aria-hidden
          className="h-2.5 w-2.5"
          viewBox="0 0 12 12"
          fill="currentColor"
        >
          <path d="M6 0L1 2.5v4C1 9.1 3.2 11.5 6 12c2.8-.5 5-2.9 5-5.5v-4L6 0z" />
        </svg>
      ) : null}
      {config.label}
    </motion.span>
  )
}
```

**Modifications to `apps/web/src/features/results/types.ts`** — add to `ModelDecision`:
```typescript
  /** Routing tier from Fast-Track engine: tier1_verified | tier2_provisional */
  tier?: string
  /** Circuit-breaker health: healthy | degraded | broken */
  healthStatus?: string
  /** Real-time p50 latency from snapshot (ms) */
  snapshotLatencyP50?: number | null
```

**Modifications to `apps/web/src/features/results/components/CategoryHighlightCard.tsx`** — add `TierBadge` import and render it after the model name:

```tsx
// Add import at top:
import { TierBadge } from "./TierBadge"

// Replace the name line inside the component:
// BEFORE:
//   <p className="mt-2 truncate text-lg font-semibold text-(--text-primary)">{model.name}</p>
// AFTER:
      <div className="mt-2 flex items-center gap-2">
        <p className="truncate text-lg font-semibold text-(--text-primary)">{model.name}</p>
        <TierBadge tier={model.tier} />
      </div>
```

Also add degraded/broken health warning below provider name (if applicable):
```tsx
{model.healthStatus === "degraded" ? (
  <p className="mt-1 text-[10px] font-medium text-amber-400">⚠ Degraded</p>
) : model.healthStatus === "broken" ? (
  <p className="mt-1 text-[10px] font-medium text-rose-400">✕ Unavailable</p>
) : null}
```

**Verify:** `cd apps/web && bun run build`
**Commit:** `feat(ui): add TierBadge component and health status indicator in CategoryHighlightCard`

---

## Batch 5: Wiring (sequential — after all above)

---

### Task 5.1: DI wiring — inject `SnapshotRepository` + `HealthRepository` into `ModelSelector` + `FallbackExecutor`
**File:** `apps/server/app/api/dependencies/orchestrator.py` (modify existing)
**Test:** none (integration — covered by existing `test_requests_route.py`)
**Depends:** 2.1, 2.2, 3.2, 3.3, 4.1

> **Implementation:** In the existing DI factory for `GatewayOrchestrator`, construct `SnapshotRepository(session)` and `HealthRepository(session)` from the same DB session. Pass to `ModelSelector(model_repository=..., snapshot_repository=..., health_repository=...)` and `FallbackExecutor(providers=..., health_repository=..., prefer_direct=True)`.

```python
# In the DI function that builds GatewayOrchestrator:
# (exact function name depends on existing code — adapt accordingly)

from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.infrastructure.db.repositories.health_repository import HealthRepository

# Inside the factory:
snapshot_repo = SnapshotRepository(session)
health_repo = HealthRepository(session)

selector = ModelSelector(
    model_repository=model_repo,
    snapshot_repository=snapshot_repo,
    health_repository=health_repo,
)

executor = FallbackExecutor(
    providers=build_provider_clients(),
    health_repository=health_repo,
    prefer_direct=True,
)
```

**Verify:** `pytest apps/server/tests/test_requests_route.py -v` (existing suite must stay green)
**Commit:** `feat(di): wire SnapshotRepository and HealthRepository into orchestrator dependencies`

---

## Implementation Notes

### Gap Decisions (Design silent → I decided)

| Gap | Decision |
|-----|----------|
| Snapshot frequency | Append-only rows; orchestrator writes after each execution. Background job for aggregation deferred to next sprint. |
| Jitter → circuit-breaker threshold | `DEGRADED=3`, `BROKEN=6` consecutive failures. Reset on any success. |
| Snapshot age validity | No TTL enforced yet — always use latest row. TTL enforcement in follow-up. |
| `ModelProfile` score type | `latency_score`/`cost_score` stay `int` in `ModelProfile`; snapshot adjustments round to nearest int before dataclass replace. |
| Discovery mode UI toggle | Not exposed in this plan. Backend flag exists; UI toggle is follow-up. |
| Shadow routing test | Deferred — design mentions it but it requires a second orchestrator instance; out of scope for this batch. |

### Test Coverage Summary

| File | Test file | Test count |
|------|-----------|-----------|
| `model_performance_snapshot.py` | via `test_snapshot_repository.py` | 4 |
| `model_health_status.py` | via `test_health_repository.py` | 5 |
| `snapshot_repository.py` | `test_snapshot_repository.py` | 4 |
| `health_repository.py` | `test_health_repository.py` | 5 |
| `snapshot_scoring.py` | `test_snapshot_scoring.py` | 5 |
| `engine.py` (v2 additions) | `test_scoring_engine_v2.py` | 5 |
| `service.py` (selector v2) | `test_model_selector_v2.py` | 4 |
| `fallback_executor.py` (v2) | `test_fallback_executor_v2.py` | 2 |
| `registry.py` (v2) | `test_provider_registry_v2.py` | 3 |
| `TierBadge.tsx` | bun build (type-check) | — |
| `gateway.py` domain types | `test_domain_gateway_types.py` | 4 |

**Total new tests: ~41 assertions across 10 test files.**
