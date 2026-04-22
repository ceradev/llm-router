"""Routing catalog scores (quality / latency / cost) live in `llm_model_routing_settings`.

They are stored as integers on a **1–10** scale (higher is better for each axis).
`0` means \"not set yet\" (e.g. OpenRouter sync before manual/benchmark curation).
"""

from __future__ import annotations

ROUTING_SCORE_MIN = 1
ROUTING_SCORE_MAX = 10
# Mid-scale default when DB still has 0 (unknown) — avoids collapsing every model to the same edge.
ROUTING_SCORE_NEUTRAL = 5


def clamp_routing_int(value: int | float) -> int:
    return int(max(ROUTING_SCORE_MIN, min(ROUTING_SCORE_MAX, int(value))))


def effective_routing_int(value: int) -> int:
    """Map DB routing integer to 1..10 for scoring; 0 → neutral."""
    if value <= 0:
        return ROUTING_SCORE_NEUTRAL
    return clamp_routing_int(value)
