from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Capability(str, Enum):
    GENERAL = "general"
    ANALYSIS = "analysis"
    CODE = "code"
    CREATIVE = "creative"
    JSON = "json"


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    provider: str
    quality_score: int
    latency_score: int
    cost_score: int
    default_temperature: float
    capabilities: set[Capability] = field(default_factory=set)

    @property
    def supports_json(self) -> bool:
        return Capability.JSON in self.capabilities

