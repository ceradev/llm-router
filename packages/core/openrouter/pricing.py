from __future__ import annotations


def compute_cost_score(total_cost: float) -> int:
    """Map OpenRouter combined prompt+completion price (per-token sum) to 1–10 routing score.

    10 = cheapest / free, 1 = most expensive. Thresholds follow the old 1–5 ladder, expanded.
    """
    if total_cost == 0:
        return 10
    if total_cost < 0.0000002:
        return 10
    if total_cost < 0.000001:
        return 9
    if total_cost < 0.000005:
        return 8
    if total_cost < 0.00001:
        return 7
    if total_cost < 0.00005:
        return 6
    if total_cost < 0.0001:
        return 5
    if total_cost < 0.0005:
        return 4
    if total_cost < 0.001:
        return 3
    if total_cost < 0.005:
        return 2
    return 1


def compute_cost_score_from_avg_usd(avg_usd: float) -> int:
    """Map observed average USD cost per benchmark case to 1–10 (10 = very cheap).

    Distinct from `compute_cost_score`, which expects OpenRouter per-token pricing totals.
    """
    if avg_usd <= 0:
        return 10
    if avg_usd < 0.0003:
        return 10
    if avg_usd < 0.0008:
        return 9
    if avg_usd < 0.002:
        return 8
    if avg_usd < 0.005:
        return 7
    if avg_usd < 0.01:
        return 6
    if avg_usd < 0.02:
        return 5
    if avg_usd < 0.04:
        return 4
    if avg_usd < 0.08:
        return 3
    if avg_usd < 0.15:
        return 2
    return 1


def parse_total_pricing(pricing: object | None) -> float:
    if not isinstance(pricing, dict):
        return 0.0

    def _f(v: object) -> float:
        if v is None:
            return 0.0
        if isinstance(v, bool):
            return 0.0
        if isinstance(v, int | float):
            return float(v)
        s = str(v).strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0

    prompt = _f(pricing.get("prompt"))
    completion = _f(pricing.get("completion"))
    return prompt + completion
