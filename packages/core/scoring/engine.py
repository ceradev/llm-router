from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import Intent, Priority
from packages.domain.models import Capability, ModelProfile


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    base_total: float
    adjusted_total: float
    model_score_adjustment: float
    quality_component: float
    latency_component: float
    cost_component: float
    priority_component: float
    routing_bonus: float
    use_case_bonus: float
    provider_bonus: float
    explanation: str
    jitter_penalty: float = 0.0
    health_multiplier: float = 1.0   # NEW: [0.3, 1.0], 1.0 = fully healthy


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


def _weights_for_intent(intent: Intent) -> tuple[float, float, float]:
    """Per-intent weight overrides applied BEFORE priority weights."""
    if intent == Intent.CODE:
        return (1.15, 0.85, 0.70)
    if intent == Intent.ANALYSIS:
        return (1.10, 0.80, 0.90)
    if intent == Intent.CREATIVE:
        return (1.20, 0.70, 0.80)
    return (1.0, 1.0, 1.0)


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
    avg_rating: float | None = None,
    ratings_count: int = 0,
    intent: Intent | None = None,
    jitter_penalty: float = 0.0,
    health_multiplier: float = 1.0,   # NEW parameter
) -> ScoreBreakdown:
    quality_weight, latency_weight, cost_weight = _weights_for_priority(priority)

    if intent is not None:
        iq, il, ic = _weights_for_intent(intent)
        quality_weight *= iq
        latency_weight *= il
        cost_weight *= ic
        quality_weight, latency_weight, cost_weight = _renormalize_weights(
            quality_weight, latency_weight, cost_weight
        )

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

    raw_base = quality_component + latency_component + cost_component + priority_component
    raw_base = max(0.0, raw_base - jitter_penalty)

    # --- NEW: apply health multiplier to base total ---
    clamped_health = max(0.3, min(1.0, health_multiplier))
    base_total = raw_base * clamped_health

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

    total_without_feedback = base_total + routing_bonus
    adjustment_factor = 1.0
    if avg_rating is not None and ratings_count >= 5:
        adjustment_factor = avg_rating / 3.0
    adjusted_total = total_without_feedback * adjustment_factor
    model_score_adjustment = adjusted_total - total_without_feedback

    explanation = (
        f"score={adjusted_total:.2f} "
        f"(quality={quality_component:.2f}, latency={latency_component:.2f}, "
        f"cost={cost_component:.2f}, priority={priority_component:.2f}, jitter={jitter_penalty:.2f}, "
        f"health_mult={clamped_health:.2f}, "
        f"routing_bonus={routing_bonus:.2f} "
        f"[capability={capability_bonus:.2f}, use_case={use_case_bonus:.2f}, provider={provider_bonus:.2f}, confidence={confidence_bonus:.2f}], "
        f"feedback_adjustment={model_score_adjustment:.2f}, feedback_factor={adjustment_factor:.2f}, "
        f"feedback_avg_rating={avg_rating if avg_rating is not None else 'n/a'}, feedback_count={ratings_count}; "
        f"priority='{priority.value}')"
    )

    return ScoreBreakdown(
        total=adjusted_total,
        base_total=base_total,
        adjusted_total=adjusted_total,
        model_score_adjustment=model_score_adjustment,
        quality_component=quality_component,
        latency_component=latency_component,
        cost_component=cost_component,
        priority_component=priority_component,
        routing_bonus=routing_bonus,
        use_case_bonus=use_case_bonus,
        provider_bonus=provider_bonus,
        explanation=explanation,
        jitter_penalty=jitter_penalty,
        health_multiplier=clamped_health,
    )


def _weights_for_priority(priority: Priority) -> tuple[float, float, float]:
    if priority == Priority.HIGH_QUALITY:
        return (1.0, 0.35, 0.25)
    if priority == Priority.LOW_LATENCY:
        return (0.35, 1.0, 0.25)
    if priority == Priority.LOW_COST:
        return (0.35, 0.25, 1.0)
    return (0.6, 0.6, 0.6)
