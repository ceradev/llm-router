from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from datetime import datetime

from packages.infrastructure.db.repositories.health_repository import HealthRepository, _BROKEN_THRESHOLD, _DEGRADED_THRESHOLD
from packages.domain.gateway import HealthState
from packages.infrastructure.db.models.model_health_status import ModelHealthStatus

@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    # Only create the table for ModelHealthStatus to avoid ARRAY issues in other models
    ModelHealthStatus.__table__.create(engine)
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
