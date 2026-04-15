# packages/services/real_time_observer/observer.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select, func, text

from packages.infrastructure.db.models.llm_attempt import LLMAttempt
from packages.services.real_time_observer.types import ModelHealthSignal, RealTimeHealthSnapshot

_MIN_HEALTH_MULTIPLIER = 0.3
_MAX_HEALTH_MULTIPLIER = 1.0
_FAILURE_WEIGHT = 0.7       # How much failure_rate drags multiplier down
_LATENCY_SPIKE_MS = 5_000   # Threshold for high-latency penalty
_LATENCY_PENALTY = 0.15     # Additional penalty when avg latency > threshold
_MIN_ATTEMPTS_FOR_SIGNAL = 2  # Ignore single-attempt noise


def _compute_health_multiplier(failure_rate: float, avg_latency_ms: float | None) -> float:
    multiplier = 1.0 - (failure_rate * _FAILURE_WEIGHT)
    if avg_latency_ms is not None and avg_latency_ms > _LATENCY_SPIKE_MS:
        multiplier -= _LATENCY_PENALTY
    return max(_MIN_HEALTH_MULTIPLIER, min(_MAX_HEALTH_MULTIPLIER, multiplier))


class RealTimeObserver:
    """Queries recent llm_attempts to produce per-model health signals.

    No new DB table required — works with the existing llm_attempts schema.
    Designed to complete in <10ms via a single GROUP BY query.
    """

    def __init__(self, session: Session, *, window_minutes: int = 10) -> None:
        self.session = session
        self.window_minutes = window_minutes

    def get_health_snapshot(
        self, routing_keys: list[str] | None = None
    ) -> RealTimeHealthSnapshot:
        """Return a health snapshot for the given routing keys.

        If routing_keys is None, returns snapshot for ALL models seen
        in the time window (useful for bulk pre-scoring).
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)

        stmt = (
            select(
                LLMAttempt.model_routing_key,
                func.count().label("total"),
                func.sum(
                    # Map status to 1/0 for failure counting
                    func.cast(LLMAttempt.status != "success", type_=None)
                ).label("failures"),
                func.avg(LLMAttempt.latency_ms).label("avg_latency"),
            )
            .where(LLMAttempt.created_at >= since)
            .group_by(LLMAttempt.model_routing_key)
        )

        if routing_keys is not None:
            stmt = stmt.where(LLMAttempt.model_routing_key.in_(routing_keys))

        rows = self.session.exec(stmt).all()

        signals: dict[str, ModelHealthSignal] = {}
        for row in rows:
            key = row.model_routing_key
            total = int(row.total or 0)
            if total < _MIN_ATTEMPTS_FOR_SIGNAL:
                continue  # Not enough data → neutral (no entry)

            failures = int(row.failures or 0)
            failure_rate = failures / total
            avg_latency = float(row.avg_latency) if row.avg_latency is not None else None
            multiplier = _compute_health_multiplier(failure_rate, avg_latency)

            signals[key] = ModelHealthSignal(
                model_routing_key=key,
                failure_rate=failure_rate,
                avg_latency_ms=avg_latency,
                attempt_count=total,
                health_multiplier=multiplier,
            )

        return RealTimeHealthSnapshot(signals=signals)
