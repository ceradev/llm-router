from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from packages.infrastructure.db.models.daily_metrics import DailyMetrics
from packages.infrastructure.db.models.llm_request import LLMRequest


class MetricsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_daily(self, target_date: date) -> DailyMetrics:
        existing = self.session.get(DailyMetrics, target_date)
        if existing:
            return existing
        metrics = DailyMetrics(metric_date=target_date)
        self.session.add(metrics)
        return metrics

    def record_request(
        self,
        *,
        session_id: str | None,
        success: bool,
        latency_ms: float,
    ) -> None:
        today = date.today()
        metrics = self.get_or_create_daily(today)

        metrics.total_requests += 1
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1

        total = metrics.successful_requests + metrics.failed_requests
        metrics.avg_latency_ms = (
            (metrics.avg_latency_ms * (total - 1) + latency_ms) / total
        )

        if session_id:
            unique_today = self._count_unique_sessions(today)
            metrics.unique_sessions = unique_today

        self.session.add(metrics)

    def _count_unique_sessions(self, target_date: date) -> int:
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        stmt = select(func.count(func.distinct(LLMRequest.session_id))).where(
            LLMRequest.created_at >= start,
            LLMRequest.created_at < end,
            LLMRequest.session_id.isnot(None),
        )
        return self.session.exec(stmt).one() or 0

    def get_summary(self, days: int = 30) -> list[DailyMetrics]:
        effective_days = max(days, 1)
        start_date = date.today() - timedelta(days=effective_days - 1)
        stmt = select(DailyMetrics).where(
            DailyMetrics.metric_date >= start_date
        ).order_by(DailyMetrics.metric_date.desc())
        return list(self.session.exec(stmt).all())

    def get_daily(self, target_date: date) -> DailyMetrics | None:
        return self.session.get(DailyMetrics, target_date)
