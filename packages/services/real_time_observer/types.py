# packages/services/real_time_observer/types.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelHealthSignal:
    """Aggregated real-time health signal for one model, derived from
    recent llm_attempts rows (last N minutes).

    failure_rate : fraction of failed attempts in the window [0.0, 1.0].
    avg_latency_ms : mean latency of successful attempts; None if no successes.
    attempt_count : total attempts seen in the window (0 = no data -> neutral).
    health_multiplier : pre-computed scalar in [0.3, 1.0] applied to base_total
        in ScoringEngine.  1.0 = fully healthy, 0.3 = severely degraded.
    """

    model_routing_key: str
    failure_rate: float          # [0.0, 1.0]
    avg_latency_ms: float | None
    attempt_count: int
    health_multiplier: float     # [0.3, 1.0]


@dataclass(frozen=True)
class RealTimeHealthSnapshot:
    """Map of routing_key -> ModelHealthSignal for all models queried."""

    signals: dict[str, ModelHealthSignal] = field(default_factory=dict)

    def get_multiplier(self, routing_key: str) -> float:
        """Return health_multiplier for key, defaulting to 1.0 (healthy)."""
        signal = self.signals.get(routing_key)
        return signal.health_multiplier if signal is not None else 1.0
