from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.catalog.types import ModelProfile


class Priority(str, Enum):
    BALANCED = "balanced"
    LOW_COST = "low_cost"
    HIGH_QUALITY = "high_quality"
    LOW_LATENCY = "low_latency"


class Intent(str, Enum):
    GENERAL = "general"
    ANALYSIS = "analysis"
    CODE = "code"
    CREATIVE = "creative"


@dataclass(frozen=True)
class GatewayTask:
    prompt: str
    priority: Priority
    temperature: float | None
    max_tokens: int | None
    require_json: bool
    simulate_failures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RoutedRequest:
    prompt: str
    temperature: float
    max_tokens: int | None
    require_json: bool
    simulate_failures: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    provider: str
    model_id: str


@dataclass(frozen=True)
class InvocationAttempt:
    provider: str
    model_id: str
    status: str
    detail: str


@dataclass(frozen=True)
class RoutingDecision:
    intent: Intent
    reason: str
    applied_temperature: float
    candidates: list[ModelProfile]


@dataclass(frozen=True)
class GatewayExecutionResult:
    response: ProviderResponse
    decision: RoutingDecision
    attempts: list[InvocationAttempt]
