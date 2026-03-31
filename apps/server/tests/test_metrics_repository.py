from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from packages.infrastructure.db.models.daily_metrics import DailyMetrics
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.repositories.metrics_repository import MetricsRepository


def _build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DailyMetrics.__table__.create(engine, checkfirst=True)
    LLMRequest.__table__.create(engine, checkfirst=True)
    return Session(engine)


def test_record_request_updates_daily_counters_and_average() -> None:
    with _build_session() as session:
        repo = MetricsRepository(session)

        repo.record_request(session_id="s-1", success=True, latency_ms=120.0)
        repo.record_request(session_id="s-1", success=False, latency_ms=80.0)
        session.commit()

        metrics = repo.get_daily(date.today())
        assert metrics is not None
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.avg_latency_ms == pytest.approx(100.0)


def test_record_request_counts_unique_sessions_from_requests_table() -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)

    with _build_session() as session:
        session.add(
            LLMRequest(
                prompt="a",
                intent="general",
                priority="normal",
                require_json=False,
                session_id="session-a",
                created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=1),
            )
        )
        session.add(
            LLMRequest(
                prompt="b",
                intent="general",
                priority="normal",
                require_json=False,
                session_id="session-a",
                created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=2),
            )
        )
        session.add(
            LLMRequest(
                prompt="c",
                intent="general",
                priority="normal",
                require_json=False,
                session_id="session-b",
                created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=3),
            )
        )
        session.add(
            LLMRequest(
                prompt="d",
                intent="general",
                priority="normal",
                require_json=False,
                session_id=None,
                created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=4),
            )
        )
        session.add(
            LLMRequest(
                prompt="e",
                intent="general",
                priority="normal",
                require_json=False,
                session_id="session-c",
                created_at=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=4),
            )
        )
        session.flush()

        repo = MetricsRepository(session)
        repo.record_request(session_id="session-a", success=True, latency_ms=40.0)
        session.commit()

        metrics = repo.get_daily(today)
        assert metrics is not None
        assert metrics.unique_sessions == 2


def test_get_summary_returns_exact_window_in_desc_order() -> None:
    with _build_session() as session:
        today = date.today()
        session.add(
            DailyMetrics(
                metric_date=today - timedelta(days=2),
                total_requests=1,
                successful_requests=1,
                failed_requests=0,
                avg_latency_ms=10.0,
                unique_sessions=1,
            )
        )
        session.add(
            DailyMetrics(
                metric_date=today - timedelta(days=1),
                total_requests=2,
                successful_requests=2,
                failed_requests=0,
                avg_latency_ms=20.0,
                unique_sessions=2,
            )
        )
        session.add(
            DailyMetrics(
                metric_date=today,
                total_requests=3,
                successful_requests=2,
                failed_requests=1,
                avg_latency_ms=30.0,
                unique_sessions=3,
            )
        )
        session.commit()

        repo = MetricsRepository(session)
        results = repo.get_summary(days=2)

        assert [item.metric_date for item in results] == [today, today - timedelta(days=1)]
