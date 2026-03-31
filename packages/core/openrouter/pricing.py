from __future__ import annotations


def compute_cost_score(total_cost: float) -> int:
    """Map OpenRouter combined prompt+completion price to 1–5 routing score."""
    if total_cost == 0:
        return 5
    if total_cost < 0.000001:
        return 4
    if total_cost < 0.00001:
        return 3
    if total_cost < 0.0001:
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
