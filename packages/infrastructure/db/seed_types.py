from __future__ import annotations

from dataclasses import dataclass

from packages.domain.models import Capability


@dataclass(frozen=True)
class SeededModelUpsertParams:
    """external_model_id: model name only (after `/` in OpenRouter `id`)."""

    source_provider: str
    external_model_id: str
    display_name: str
    supports_json: bool
    supports_tools: bool
    supports_vision: bool
    tier: str
    context_window: int | None
    max_output_tokens: int | None
    quality_score: int
    latency_score: int
    cost_score: int
    capabilities: frozenset[Capability]
    default_temperature: float = 0.2
    priority_weight: int = 100
