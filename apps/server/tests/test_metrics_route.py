from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.metrics import router as metrics_router
from packages.infrastructure.db.models.daily_metrics import DailyMetrics


def _seed_daily(session: Session) -> None:
    session.add(
        DailyMetrics(
            metric_date=date.today(),
            total_requests=10,
            successful_requests=7,
            failed_requests=3,
            avg_latency_ms=150.0,
            unique_sessions=4,
        )
    )
    session.commit()


@pytest.fixture
def metrics_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DailyMetrics.__table__.create(engine, checkfirst=True)

    with Session(engine) as session:
        _seed_daily(session)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.include_router(metrics_router)
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_daily_endpoint_uses_date_query_param(metrics_client: TestClient) -> None:
    response = metrics_client.get(f"/v1/metrics/daily?date={date.today().isoformat()}")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == date.today().isoformat()
    assert body["total_requests"] == 10


def test_daily_endpoint_accepts_legacy_date_str_param(metrics_client: TestClient) -> None:
    response = metrics_client.get(f"/v1/metrics/daily?date_str={date.today().isoformat()}")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == date.today().isoformat()


def test_summary_days_has_lower_bound_validation(metrics_client: TestClient) -> None:
    response = metrics_client.get("/v1/metrics/summary?days=0")
    assert response.status_code == 422
