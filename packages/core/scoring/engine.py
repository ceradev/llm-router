from __future__ import annotations

from dataclasses import dataclass
import math

from packages.core.routing_scores import effective_routing_int
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
    health_multiplier: float = 1.0
    feedback_factor: float = 1.0
    health_effective: float = 1.0
    feedback_effective: float = 1.0
    exploration_bonus: float = 0.0
    alpha: float = 1.2
    reasoning_score: float = 0.0
    latency_score: float = 0.0
    cost_score: float = 0.0
    context_score: float = 0.0
    context_headroom: float = 0.0
    capability_score: float = 0.0
    capability_prior: float = 0.0
    capability_adjustment: float = 0.0
    capability_confidence: float = 1.0
    capability_reason: str = "none"
    reasoning_weight: float = 0.25
    latency_weight: float = 0.25
    cost_weight: float = 0.25
    context_weight: float = 0.25


@dataclass(frozen=True)
class CapabilityRoutingConfig:
    max_capability_delta: float = 0.10
    capability_prior_weight: float = 0.06
    premium_near_top_gap: float = 0.08
    premium_near_top_boost: float = 0.03
    low_tier_overperformance_threshold: float = 0.18
    low_tier_overperformance_penalty: float = 0.02
    low_confidence_threshold: float = 0.80
    confidence_capability_weight: float = 0.10
    gap_prefer_capability_threshold: float = 0.025
    high_complexity_threshold: float = 0.70
    complexity_capability_weight_boost: float = 0.05
    complexity_reasoning_weight_boost: float = 0.05


@dataclass(frozen=True)
class PromptFeatures:
    complexity_score: float
    estimated_tokens: int
    requires_reasoning: bool
    requires_code: bool
    priority: Priority


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def normalize(
    value: float,
    lo: float,
    hi: float,
    *,
    invert: bool = False,
    gamma: float = 1.0,
    eps: float = 1e-9,
) -> float:
    span = max(hi - lo, eps)
    x = clamp((value - lo) / span, 0.0, 1.0)
    if invert:
        x = 1.0 - x
    return clamp(x**gamma, 0.0, 1.0)


def _estimate_latency_ms_from_score(latency_score: float) -> float:
    s = float(effective_routing_int(int(latency_score)))
    s = clamp(s, 1.0, 10.0)
    # 1=slow (~4000ms), 10=fast (~500ms)
    return 4000.0 - ((s - 1.0) / 9.0) * 3500.0


def _estimate_cost_per_1k_from_score(cost_score: float) -> float:
    s = float(effective_routing_int(int(cost_score)))
    s = clamp(s, 1.0, 10.0)
    # 1=expensive (~$0.03), 10=cheap (~$0.0008)
    return 0.03 - ((s - 1.0) / 9.0) * (0.03 - 0.0008)


def _estimate_cost_per_1k_from_prices(model: ModelProfile) -> float | None:
    if model.prompt_price is None and model.completion_price is None:
        return None
    prompt = max(0.0, float(model.prompt_price or 0.0))
    completion = max(0.0, float(model.completion_price or 0.0))
    # Prices are stored per token; convert to per-1k-token average.
    return ((prompt + completion) / 2.0) * 1000.0


def compute_reasoning_score(
    *,
    model: ModelProfile,
    complexity_score: float,
    requires_reasoning: bool,
    requires_code: bool,
) -> float:
    # Routing quality is on 1..10 in `llm_model_routing_settings` (0 = unknown → neutral).
    quality = normalize(float(effective_routing_int(model.quality_score)), 1.0, 10.0, gamma=1.15)
    capability_boost = 1.0
    if requires_reasoning:
        capability_boost += 0.08
    if requires_code and Capability.CODE in model.capabilities:
        capability_boost += 0.05
    complexity_boost = 1.0 + 0.12 * clamp(complexity_score, 0.0, 1.0)
    return clamp(quality * capability_boost * complexity_boost, 0.0, 1.0)


def compute_latency_score(latency_ms: float, latency_scale_ms: float = 1500.0) -> float:
    return clamp(math.exp(-max(latency_ms, 0.0) / latency_scale_ms), 0.0, 1.0)


def compute_cost_score(cost_per_1k_tokens: float, cost_scale: float = 120.0) -> float:
    return clamp(math.exp(-max(cost_per_1k_tokens, 0.0) * cost_scale), 0.0, 1.0)


def compute_context_score(prompt_tokens: int, context_window: int) -> tuple[float, float]:
    if context_window <= 0:
        return 0.0, 0.0
    if prompt_tokens > context_window:
        return 0.0, 0.0

    usage = prompt_tokens / float(max(context_window, 1))
    headroom = clamp(1.0 - usage, 0.0, 1.0)
    penalty = 1.0 / (1.0 + math.exp(-((usage - 0.88) / 0.08)))
    score = clamp(1.0 - penalty, 0.0, 1.0)
    return score, headroom


def compute_health_multiplier(failure_rate: float, avg_latency_ms: float | None) -> float:
    multiplier = 1.0 - (clamp(failure_rate, 0.0, 1.0) * 0.7)
    if avg_latency_ms is not None and avg_latency_ms > 5000.0:
        multiplier -= 0.15
    return clamp(multiplier, 0.35, 1.0)


def compute_feedback_factor(
    *,
    avg_rating: float | None,
    ratings_count: int,
    prior_rating: float = 3.8,
    k: int = 20,
    gain: float = 0.08,
) -> float:
    if avg_rating is None or ratings_count <= 0:
        return 1.0
    n = float(max(0, ratings_count))
    shrunk = ((n / (n + k)) * float(avg_rating)) + ((k / (n + k)) * prior_rating)
    return clamp(1.0 + gain * (shrunk - prior_rating), 0.90, 1.10)


def derive_dynamic_weights(prompt_features: PromptFeatures) -> dict[str, float]:
    by_priority: dict[Priority, dict[str, float]] = {
        Priority.HIGH_QUALITY: {"wr": 0.50, "wl": 0.20, "wc": 0.15, "wx": 0.15},
        Priority.LOW_LATENCY: {"wr": 0.20, "wl": 0.50, "wc": 0.20, "wx": 0.10},
        Priority.LOW_COST: {"wr": 0.20, "wl": 0.20, "wc": 0.50, "wx": 0.10},
        Priority.BALANCED: {"wr": 0.35, "wl": 0.25, "wc": 0.20, "wx": 0.20},
    }
    w = dict(by_priority[prompt_features.priority])
    complexity = clamp(prompt_features.complexity_score, 0.0, 1.0)

    if prompt_features.estimated_tokens > 2200:
        w["wx"] += 0.10
        w["wl"] -= 0.04
        w["wc"] -= 0.03
        w["wr"] -= 0.03
    if complexity > 0.70:
        w["wr"] += 0.10
        w["wl"] -= 0.05
        w["wc"] -= 0.05
    if complexity < 0.35:
        w["wl"] += 0.06
        w["wc"] += 0.06
        w["wr"] -= 0.08
        w["wx"] -= 0.04

    for key in ("wr", "wl", "wc", "wx"):
        w[key] = clamp(w[key], 0.10, 0.70)
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def _provider_and_use_case_bonus(
    *,
    model: ModelProfile,
    use_cases: list[str] | None,
    preferred_providers: list[str] | None,
    requires_tools: bool,
) -> tuple[float, float]:
    use_case_bonus = 0.0
    if use_cases:
        normalized = {u.lower() for u in use_cases}
        if "api" in normalized and model.supports_json:
            use_case_bonus += 0.06
        if ("ide" in normalized or "chatbot" in normalized) and model.supports_tools:
            use_case_bonus += 0.05
    if requires_tools and model.supports_tools:
        use_case_bonus += 0.04

    provider_bonus = 0.0
    if preferred_providers:
        preferred = {p.lower() for p in preferred_providers}
        if model.provider.lower() in preferred:
            provider_bonus += 0.05
    return use_case_bonus, provider_bonus


def _confidence_bonus(model: ModelProfile) -> float:
    return 0.04 if (model.evaluation_status or "").strip().lower() == "verified" else 0.0


def _exploration_bonus(
    *,
    complexity_score: float,
    requires_reasoning: bool,
    exploration_enabled: bool,
    total_attempts: int,
    model_attempts: int,
    exploration_c: float,
) -> float:
    if not exploration_enabled:
        return 0.0
    if requires_reasoning or complexity_score >= 0.75:
        return 0.0
    total = max(0, total_attempts)
    seen = max(0, model_attempts)
    raw = exploration_c * math.sqrt(math.log(total + 1.0) / (seen + 1.0))
    damped = raw * ((1.0 - clamp(complexity_score, 0.0, 1.0)) ** 1.5)
    return clamp(damped, 0.0, 0.10)


def _tier_bucket(raw_tier: str | None) -> str:
    tier = (raw_tier or "").strip().lower()
    if tier in {"premium", "tier1", "enterprise"}:
        return "premium"
    if tier in {"free", "budget", "economy"}:
        return "budget"
    return "standard"


def _capability_confidence(evaluation_status: str) -> float:
    status = (evaluation_status or "").strip().lower()
    if status == "verified":
        return 1.0
    if status == "provisional":
        return 0.85
    if status == "cataloged":
        return 0.72
    return 0.78


def _lerp(min_value: float, max_value: float, factor: float) -> float:
    t = clamp(factor, 0.0, 1.0)
    return min_value + ((max_value - min_value) * t)


def _derive_capability_score(model: ModelProfile, explicit: float | None = None) -> float:
    if explicit is not None:
        return clamp(float(explicit), 0.0, 1.0)

    base_by_tier = {
        "premium": 0.78,
        "standard": 0.62,
        "budget": 0.48,
    }
    tier = _tier_bucket(model.tier)
    capability = base_by_tier[tier]

    status = (model.evaluation_status or "").strip().lower()
    if status == "verified":
        capability += 0.08
    elif status == "provisional":
        capability += 0.03
    elif status == "cataloged":
        capability -= 0.02

    if Capability.CODE in model.capabilities:
        capability += 0.03
    if Capability.ANALYSIS in model.capabilities:
        capability += 0.02
    if model.supports_tools:
        capability += 0.02
    if model.supports_json:
        capability += 0.01
    if int(model.context_window or 0) >= 128_000:
        capability += 0.02

    return clamp(capability, 0.20, 0.98)


def apply_capability_prior(
    *,
    model: ModelProfile,
    complexity_score: float,
    capability_score: float | None = None,
    config: CapabilityRoutingConfig | None = None,
) -> tuple[float, float]:
    cfg = config or CapabilityRoutingConfig()
    resolved_capability = _derive_capability_score(model=model, explicit=capability_score)
    complexity = clamp(complexity_score, 0.0, 1.0)
    complexity_factor = 0.70 + (0.60 * complexity)
    prior = (resolved_capability - 0.5) * cfg.capability_prior_weight * complexity_factor
    # Bound prior influence so capability cannot dominate measured operational signals.
    return resolved_capability, clamp(prior, -0.06, 0.08)


def should_apply_low_tier_penalty(
    *,
    model: ModelProfile,
    score: float,
    expected: float,
    confidence: float,
    config: CapabilityRoutingConfig | None = None,
) -> bool:
    cfg = config or CapabilityRoutingConfig()
    if _tier_bucket(model.tier) != "budget":
        return False
    # Only penalize uncertain low-tier spikes; high-confidence budget wins remain allowed.
    if confidence >= cfg.low_confidence_threshold:
        return False
    return (score - expected) > cfg.low_tier_overperformance_threshold


def adjust_score_with_capability(
    *,
    model: ModelProfile,
    current_score: float,
    capability_score: float,
    reasoning_score: float,
    complexity_score: float,
    top_reference_score: float | None = None,
    confidence: float | None = None,
    include_reason: bool = False,
    config: CapabilityRoutingConfig | None = None,
) -> tuple[float, float, float] | tuple[float, float, float, str]:
    cfg = config or CapabilityRoutingConfig()
    tier = _tier_bucket(model.tier)
    complexity = clamp(complexity_score, 0.0, 1.0)
    resolved_confidence = confidence if confidence is not None else _capability_confidence(model.evaluation_status)
    influence_scale = _lerp(0.3, 1.0, complexity)
    reason = "none"

    capability_weight = cfg.confidence_capability_weight
    if complexity >= cfg.high_complexity_threshold:
        capability_weight += cfg.complexity_capability_weight_boost
    else:
        capability_weight = max(0.03, capability_weight - 0.03)

    reasoning_factor = 0.0
    if complexity >= cfg.high_complexity_threshold:
        high_span = max(1e-6, 1.0 - cfg.high_complexity_threshold)
        high_norm = (complexity - cfg.high_complexity_threshold) / high_span
        reasoning_factor = cfg.complexity_reasoning_weight_boost * clamp(high_norm, 0.0, 1.0)

    confidence_delta = capability_weight * (capability_score - 0.5) * resolved_confidence
    reasoning_delta = reasoning_factor * (reasoning_score - 0.5)
    premium_delta = 0.0
    if top_reference_score is not None and tier == "premium":
        score_gap = max(0.0, top_reference_score - current_score)
        if score_gap <= cfg.premium_near_top_gap:
            proximity = 1.0 - (score_gap / max(cfg.premium_near_top_gap, 1e-6))
            premium_delta = cfg.premium_near_top_boost * proximity * (0.7 + 0.3 * resolved_confidence)
            reason = "premium_near_tie_boost"

    low_tier_penalty = 0.0
    normalized_score = clamp(current_score / 2.0, 0.0, 1.0)
    if should_apply_low_tier_penalty(
        model=model,
        score=normalized_score,
        expected=capability_score,
        confidence=resolved_confidence,
        config=cfg,
    ):
        excess = (normalized_score - capability_score) - cfg.low_tier_overperformance_threshold
        low_tier_penalty = cfg.low_tier_overperformance_penalty + min(0.04, max(0.0, excess) * 0.10)
        reason = "low_confidence_penalty"

    if reason == "none" and reasoning_delta > 1e-9:
        reason = "complexity_boost"

    adjustment = (confidence_delta + reasoning_delta + premium_delta - low_tier_penalty) * influence_scale
    adjustment = clamp(adjustment, -0.08, 0.08)
    if include_reason:
        return clamp(current_score + adjustment, 0.0, 2.4), adjustment, resolved_confidence, reason
    return clamp(current_score + adjustment, 0.0, 2.4), adjustment, resolved_confidence


def apply_gap_decision(
    *,
    ranked_items: list[tuple[float, float, float, str]],
    gap_threshold: float | None = None,
    config: CapabilityRoutingConfig | None = None,
) -> list[str]:
    cfg = config or CapabilityRoutingConfig()
    threshold = cfg.gap_prefer_capability_threshold if gap_threshold is None else max(0.0, gap_threshold)
    if len(ranked_items) <= 1:
        return [item[3] for item in ranked_items]

    working = list(ranked_items)
    for idx in range(len(working) - 1):
        first = working[idx]
        second = working[idx + 1]
        score_gap = abs(first[0] - second[0])
        if score_gap > threshold:
            continue
        first_effective_cap = first[1] * first[2]
        second_effective_cap = second[1] * second[2]
        # Deterministic near-tie policy: effective capability, then raw capability, then model_id.
        second_is_better = (
            second_effective_cap > first_effective_cap + 0.01
            or (
                abs(second_effective_cap - first_effective_cap) <= 0.01
                and (
                    second[1] > first[1] + 1e-9
                    or (abs(second[1] - first[1]) <= 1e-9 and second[3] < first[3])
                )
            )
        )
        if second_is_better:
            working[idx], working[idx + 1] = second, first

    return [item[3] for item in working]


def integrate_with_existing_score(
    *,
    model: ModelProfile,
    pre_capability_score: float,
    reasoning_score: float,
    complexity_score: float,
    capability_score: float | None = None,
    top_reference_score: float | None = None,
    config: CapabilityRoutingConfig | None = None,
) -> tuple[float, float, float, float, float, str]:
    cfg = config or CapabilityRoutingConfig()
    resolved_capability, capability_prior = apply_capability_prior(
        model=model,
        complexity_score=complexity_score,
        capability_score=capability_score,
        config=cfg,
    )
    confidence = _capability_confidence(model.evaluation_status)
    with_prior = clamp(pre_capability_score + capability_prior, 0.0, 2.4)
    _capability_adjusted, adjustment, confidence, reason = adjust_score_with_capability(
        model=model,
        current_score=with_prior,
        capability_score=resolved_capability,
        reasoning_score=reasoning_score,
        complexity_score=complexity_score,
        top_reference_score=top_reference_score,
        confidence=confidence,
        include_reason=True,
        config=cfg,
    )
    total_capability_delta = capability_prior + adjustment
    # Global cap prevents cumulative bias from prior + adjustment layers.
    if abs(total_capability_delta) > cfg.max_capability_delta:
        total_capability_delta = math.copysign(cfg.max_capability_delta, total_capability_delta)
    final_total = clamp(pre_capability_score + total_capability_delta, 0.0, 2.4)
    adjustment_after_cap = total_capability_delta - capability_prior
    return final_total, resolved_capability, capability_prior, adjustment_after_cap, confidence, reason


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
    health_multiplier: float = 1.0,
    failure_rate: float = 0.0,
    avg_latency_ms: float | None = None,
    observed_latency_ms: float | None = None,
    observed_cost_per_1k_tokens: float | None = None,
    prompt_tokens: int = 0,
    exploration_enabled: bool = False,
    model_attempts: int = 0,
    total_attempts: int = 0,
    exploration_c: float = 0.08,
    capability_score: float | None = None,
    top_reference_score: float | None = None,
    capability_config: CapabilityRoutingConfig | None = None,
) -> ScoreBreakdown:
    complexity = clamp(complexity_score or 0.0, 0.0, 1.0)
    if intent == Intent.CODE:
        complexity = clamp(complexity + 0.05, 0.0, 1.0)
    elif intent == Intent.CREATIVE:
        complexity = clamp(complexity - 0.03, 0.0, 1.0)
    features = PromptFeatures(
        complexity_score=complexity,
        estimated_tokens=max(0, prompt_tokens),
        requires_reasoning=requires_reasoning,
        requires_code=requires_code,
        priority=priority,
    )
    weights = derive_dynamic_weights(features)

    reasoning_score = compute_reasoning_score(
        model=model,
        complexity_score=complexity,
        requires_reasoning=requires_reasoning,
        requires_code=requires_code,
    )

    latency_ms = observed_latency_ms
    if latency_ms is None:
        latency_ms = _estimate_latency_ms_from_score(float(model.latency_score))
    latency_score = compute_latency_score(latency_ms)

    cost_per_1k = observed_cost_per_1k_tokens
    if cost_per_1k is None:
        cost_per_1k = _estimate_cost_per_1k_from_prices(model)
    if cost_per_1k is None:
        cost_per_1k = _estimate_cost_per_1k_from_score(float(model.cost_score))
    cost_score = compute_cost_score(cost_per_1k)

    context_window = int(model.context_window or 0)
    context_score, context_headroom = compute_context_score(
        prompt_tokens=max(0, prompt_tokens),
        context_window=context_window,
    )

    weighted_sum = (
        weights["wr"] * reasoning_score
        + weights["wl"] * latency_score
        + weights["wc"] * cost_score
        + weights["wx"] * context_score
    )

    use_case_bonus, provider_bonus = _provider_and_use_case_bonus(
        model=model,
        use_cases=use_cases,
        preferred_providers=preferred_providers,
        requires_tools=requires_tools,
    )
    confidence_bonus = _confidence_bonus(model)
    routing_bonus = use_case_bonus + provider_bonus + confidence_bonus
    priority_component = clamp(float(priority_weight) / 1000.0, 0.0, 0.20)

    raw_base = clamp(weighted_sum + routing_bonus + priority_component - jitter_penalty, 0.0, 2.0)
    alpha = 1.2
    shaped = (raw_base + 1e-3) ** alpha

    computed_health = compute_health_multiplier(failure_rate=failure_rate, avg_latency_ms=avg_latency_ms)
    clamped_health = clamp(min(computed_health, health_multiplier), 0.35, 1.0)
    health_effective = 0.6 + 0.4 * clamped_health

    feedback_factor = compute_feedback_factor(avg_rating=avg_rating, ratings_count=ratings_count)
    feedback_effective = clamp(1.0 + 0.5 * (feedback_factor - 1.0), 0.95, 1.05)

    exploration_bonus = _exploration_bonus(
        complexity_score=complexity,
        requires_reasoning=requires_reasoning,
        exploration_enabled=exploration_enabled,
        total_attempts=total_attempts,
        model_attempts=model_attempts,
        exploration_c=exploration_c,
    )

    pre_capability_total = (shaped * health_effective * feedback_effective) + exploration_bonus
    capability_adjusted_total, resolved_capability, capability_prior, capability_adjustment, capability_confidence, capability_reason = (
        integrate_with_existing_score(
            model=model,
            pre_capability_score=pre_capability_total,
            reasoning_score=reasoning_score,
            complexity_score=complexity,
            capability_score=capability_score,
            top_reference_score=top_reference_score,
            config=capability_config,
        )
    )

    adjusted_total = shaped * health_effective * feedback_effective
    final_total = capability_adjusted_total
    model_score_adjustment = final_total - shaped

    quality_component = weights["wr"] * reasoning_score
    latency_component = weights["wl"] * latency_score
    cost_component = weights["wc"] * cost_score
    explanation = (
        f"score={final_total:.4f} base={raw_base:.4f} shaped={shaped:.4f} "
        f"(R={reasoning_score:.3f},L={latency_score:.3f},C={cost_score:.3f},X={context_score:.3f}; "
        f"w=({weights['wr']:.2f},{weights['wl']:.2f},{weights['wc']:.2f},{weights['wx']:.2f}); "
        f"Cap={resolved_capability:.3f},CapPrior={capability_prior:+.3f},CapAdj={capability_adjustment:+.3f},CapReason={capability_reason},"
        f"H={clamped_health:.2f}->{health_effective:.2f}, "
        f"F={feedback_factor:.2f}->{feedback_effective:.2f}, "
        f"bonus={{routing:{routing_bonus:.3f},explore:{exploration_bonus:.3f},priority:{priority_component:.3f}}})"
    )

    return ScoreBreakdown(
        total=final_total,
        base_total=shaped,
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
        feedback_factor=feedback_factor,
        health_effective=health_effective,
        feedback_effective=feedback_effective,
        exploration_bonus=exploration_bonus,
        alpha=alpha,
        reasoning_score=reasoning_score,
        latency_score=latency_score,
        cost_score=cost_score,
        context_score=context_score,
        context_headroom=context_headroom,
        capability_score=resolved_capability,
        capability_prior=capability_prior,
        capability_adjustment=capability_adjustment,
        capability_confidence=capability_confidence,
        capability_reason=capability_reason,
        reasoning_weight=weights["wr"],
        latency_weight=weights["wl"],
        cost_weight=weights["wc"],
        context_weight=weights["wx"],
    )
