from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from packages.domain.models import ModelProfile


class Priority(str, Enum):
    BALANCED = "balanced"
    LOW_COST = "low_cost"
    HIGH_QUALITY = "high_quality"
    LOW_LATENCY = "low_latency"


class ModelTier(str, Enum):
    TIER1_VERIFIED = "tier1_verified"
    TIER2_PROVISIONAL = "tier2_provisional"


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"


class Intent(str, Enum):
    GENERAL = "general"
    ANALYSIS = "analysis"
    CODE = "code"
    CREATIVE = "creative"


def intent_from_evaluation_string(value: str) -> Intent:
    """Map prompt-evaluator intent labels to domain Intent."""
    key = value.strip().lower()
    mapping = {
        "code": Intent.CODE,
        "analysis": Intent.ANALYSIS,
        "creative": Intent.CREATIVE,
        "general": Intent.GENERAL,
    }
    return mapping.get(key, Intent.GENERAL)


@dataclass(frozen=True)
class GatewayTask:
    prompt: str
    priority: Priority
    temperature: float | None
    max_tokens: int | None
    require_json: bool
    max_cost_usd: float | None = None
    discovery_mode: bool = False
    simulate_failures: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    preferred_providers: list[str] = field(default_factory=list)
    response_depth: str = "balanced"


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
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost: float = 0.0


@dataclass(frozen=True)
class InvocationAttempt:
    provider: str
    model_id: str
    status: str
    detail: str
    latency_ms: int | None = None


@dataclass(frozen=True)
class RankingHighlight:
    """One model slot in the user-facing ranking summary (not debug scoring)."""

    model_id: str
    display_name: str
    provider: str
    reason_key: str
    same_as_best_overall: bool = False


@dataclass(frozen=True)
class RankingSummary:
    best_overall: RankingHighlight
    free_alternative: RankingHighlight | None
    best_quality: RankingHighlight
    best_cost: RankingHighlight
    best_speed: RankingHighlight


@dataclass(frozen=True)
class ScoredCandidate:
    model: ModelProfile
    priority_weight: int
    db_model_id: int
    rank: int
    quality_score: float
    latency_score: float
    cost_score: float
    final_score: float
    model_score_adjustment: float
    explanation: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    tier: ModelTier = ModelTier.TIER2_PROVISIONAL
    health_status: HealthState = HealthState.HEALTHY
    snapshot_latency_p50: float | None = None
    user_rating: float | None = None
    user_rating_count: int = 0


@dataclass(frozen=True)
class RoutingDecision:
    intent: Intent
    reason: str
    applied_temperature: float
    candidates: list[ModelProfile]
    scored_candidates: tuple[ScoredCandidate, ...]
    preferred_providers: list[str] = field(default_factory=list)
    preferred_providers_applied: bool = False
    preferred_providers_fallback_used: bool = False


@dataclass(frozen=True)
class FallbackExecutionOutcome:
    response: ProviderResponse
    attempts: list[InvocationAttempt]


@dataclass(frozen=True)
class GatewayExecutionResult:
    request_id: UUID
    response: ProviderResponse
    decision: RoutingDecision
    attempts: list[InvocationAttempt]
    fallback_used: bool
    ranking_summary: RankingSummary


class NoModelsAvailableError(RuntimeError):
    """Raised when there are no database routing candidates for the request."""
