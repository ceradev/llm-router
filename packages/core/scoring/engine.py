from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import Priority
from packages.domain.models import Capability, ModelProfile


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    quality_component: float
    latency_component: float
    cost_component: float
    priority_component: float
    routing_bonus: float
    use_case_bonus: float
    provider_bonus: float
    explanation: str


def _renormalize_weights(
    quality_weight: float,
    latency_weight: float,
    cost_weight: float,
) -> tuple[float, float, float]:
    s = quality_weight + latency_weight + cost_weight
    return quality_weight / s, latency_weight / s, cost_weight / s


def _routing_bonuses(
    *,
    model: ModelProfile,
    requires_code: bool,
    requires_tools: bool,
    uc_norm: set[str],
    preferred_providers: list[str] | None,
) -> tuple[float, float, float]:
    capability_bonus = 0.0
    if requires_code and Capability.CODE in model.capabilities:
        capability_bonus += 0.12
    if requires_tools and model.supports_tools:
        capability_bonus += 0.08

    use_case_bonus = 0.0
    if uc_norm:
        if "api" in uc_norm and model.supports_json:
            use_case_bonus += 0.10
        if ("ide" in uc_norm or "chatbot" in uc_norm) and model.supports_tools:
            use_case_bonus += 0.08

    provider_bonus = 0.0
    if preferred_providers:
        pref = {p.lower() for p in preferred_providers}
        if model.provider.lower() in pref:
            provider_bonus += 0.15

    return capability_bonus, use_case_bonus, provider_bonus


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
) -> ScoreBreakdown:
    quality_weight, latency_weight, cost_weight = _weights_for_priority(priority)

    if (
        priority == Priority.BALANCED
        and complexity_score is not None
        and complexity_score > 0.6
    ):
        quality_weight *= 1.08
        latency_weight *= 0.96
        cost_weight *= 0.96
        quality_weight, latency_weight, cost_weight = _renormalize_weights(
            quality_weight, latency_weight, cost_weight
        )

    uc_norm = {u.lower() for u in use_cases} if use_cases else set()
    if "chatbot" in uc_norm:
        latency_weight *= 1.08
        quality_weight, latency_weight, cost_weight = _renormalize_weights(
            quality_weight, latency_weight, cost_weight
        )

    reasoning_mult = 1.15 if requires_reasoning else 1.0
    quality_component = float(model.quality_score) * quality_weight * reasoning_mult
    latency_component = float(model.latency_score) * latency_weight
    cost_component = float(model.cost_score) * cost_weight
    priority_component = float(priority_weight) / 100.0

    base_total = quality_component + latency_component + cost_component + priority_component

    confidence_bonus = 0.0
    try:
        status = (model.evaluation_status or "").strip().lower()
    except Exception:
        status = ""
    if status == "verified":
        confidence_bonus = 0.08

    capability_bonus, use_case_bonus, provider_bonus = _routing_bonuses(
        model=model,
        requires_code=requires_code,
        requires_tools=requires_tools,
        uc_norm=uc_norm,
        preferred_providers=preferred_providers,
    )
    routing_bonus = capability_bonus + use_case_bonus + provider_bonus + confidence_bonus

    total = base_total + routing_bonus

    explanation = (
        f"score={total:.2f} "
        f"(quality={quality_component:.2f}, latency={latency_component:.2f}, "
        f"cost={cost_component:.2f}, priority={priority_component:.2f}, "
        f"routing_bonus={routing_bonus:.2f} "
        f"[capability={capability_bonus:.2f}, use_case={use_case_bonus:.2f}, provider={provider_bonus:.2f}, confidence={confidence_bonus:.2f}]; "
        f"priority='{priority.value}')"
    )

    return ScoreBreakdown(
        total=total,
        quality_component=quality_component,
        latency_component=latency_component,
        cost_component=cost_component,
        priority_component=priority_component,
        routing_bonus=routing_bonus,
        use_case_bonus=use_case_bonus,
        provider_bonus=provider_bonus,
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
