from __future__ import annotations

MAIN_PROVIDERS = frozenset({"openai", "anthropic", "google", "meta", "deepseek"})


def classify_tier(*, source_provider: str, total_cost: float) -> str:
    sp = (source_provider or "").strip().lower()
    if sp in MAIN_PROVIDERS or sp.startswith("meta-"):
        return "premium"
    if total_cost == 0:
        return "free"
    return "alternative"


def should_auto_enable_for_routing(
    *,
    cost_score: int,
    supports_json: bool,
    supports_tools: bool,
    tier: str,
    total_cost: float,
) -> bool:
    if cost_score >= 3 and (supports_json or supports_tools):
        return True
    if tier == "free" and total_cost == 0:
        return True
    if tier == "premium" and cost_score >= 3:
        return True
    return False
