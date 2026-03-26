from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import Priority
from packages.domain.models import ModelProfile


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    quality_component: float
    latency_component: float
    cost_component: float
    priority_component: float
    explanation: str


def compute_model_score(
    *,
    model: ModelProfile,
    priority: Priority,
    priority_weight: int,
) -> ScoreBreakdown:
    quality_weight, latency_weight, cost_weight = _weights_for_priority(priority)

    quality_component = float(model.quality_score) * quality_weight
    latency_component = float(model.latency_score) * latency_weight
    cost_component = float(model.cost_score) * cost_weight
    priority_component = float(priority_weight) / 100.0

    total = quality_component + latency_component + cost_component + priority_component

    explanation = (
        f"score={total:.2f} "
        f"(quality={quality_component:.2f}, latency={latency_component:.2f}, "
        f"cost={cost_component:.2f}, priority={priority_component:.2f}; "
        f"priority='{priority.value}')"
    )

    return ScoreBreakdown(
        total=total,
        quality_component=quality_component,
        latency_component=latency_component,
        cost_component=cost_component,
        priority_component=priority_component,
        explanation=explanation,
    )


def _weights_for_priority(priority: Priority) -> tuple[float, float, float]:
    if priority == Priority.HIGH_QUALITY:
        return (1.0, 0.35, 0.25)
    if priority == Priority.LOW_LATENCY:
        return (0.35, 1.0, 0.25)
    if priority == Priority.LOW_COST:
        return (0.35, 0.25, 1.0)
    return (0.6, 0.6, 0.6)

