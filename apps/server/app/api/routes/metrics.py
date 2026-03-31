from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies.orchestrator import get_db_session
from packages.infrastructure.db.models.daily_metrics import DailyMetrics
from packages.infrastructure.db.repositories.metrics_repository import MetricsRepository
from sqlmodel import Session

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


class DailyMetricsResponse(BaseModel):
    date: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    unique_sessions: int
    success_rate: float

    @classmethod
    def from_model(cls, m: DailyMetrics) -> "DailyMetricsResponse":
        total = m.total_requests or 1
        success_rate = m.successful_requests / total
        return cls(
            date=str(m.metric_date),
            total_requests=m.total_requests,
            successful_requests=m.successful_requests,
            failed_requests=m.failed_requests,
            avg_latency_ms=round(m.avg_latency_ms, 2),
            unique_sessions=m.unique_sessions,
            success_rate=round(success_rate, 3),
        )


class MetricsSummaryResponse(BaseModel):
    days: list[DailyMetricsResponse]
    totals: dict


@router.get("/summary")
def get_metrics_summary(
    session: Annotated[Session, Depends(get_db_session)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> MetricsSummaryResponse:
    repo = MetricsRepository(session)
    metrics = repo.get_summary(days=days)

    totals = {
        "total_requests": sum(m.total_requests for m in metrics),
        "successful_requests": sum(m.successful_requests for m in metrics),
        "failed_requests": sum(m.failed_requests for m in metrics),
        "unique_sessions": max(m.unique_sessions for m in metrics) if metrics else 0,
    }

    return MetricsSummaryResponse(
        days=[DailyMetricsResponse.from_model(m) for m in metrics],
        totals=totals,
    )


@router.get(
    "/daily",
    responses={
        400: {"description": "Invalid date format. Use YYYY-MM-DD."},
        404: {"description": "No metrics found for requested date."},
    },
)
def get_metrics_daily(
    session: Annotated[Session, Depends(get_db_session)],
    date_value: Annotated[str | None, Query(alias="date")] = None,
    date_str: Annotated[str | None, Query()] = None,
) -> DailyMetricsResponse:
    raw_date = date_value or date_str
    if raw_date is None:
        raise HTTPException(status_code=400, detail="Missing required query param: date")

    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    repo = MetricsRepository(session)
    metrics = repo.get_daily(target_date)

    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics for that date")

    return DailyMetricsResponse.from_model(metrics)
