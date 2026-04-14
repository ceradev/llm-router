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
