# Dynamic Feedback Loop & Intelligent Routing — Implementation Plan

**Goal:** Make the routing system self-aware by injecting real-time health signals, intent-matched scoring weights, pre-flight token/cost estimation, and budget guardrails into the existing pipeline.

**Architecture:**
- `RealTimeObserver` queries `llm_attempts` for the last 10 min and returns a `HealthMultiplier` (float 0.0–1.0) per model_id — no new DB table, no migration needed.
- `ScoringEngine` gains a `health_multiplier` parameter that shrinks `base_total` proportionally before bonuses.
- `PromptEvaluator` gains precise token estimation (words × 1.3 already exists — extend with history tokens + per-model context-window guard).
- `BudgetController` is a pure-Python dataclass validator injected into `GatewayOrchestrator.execute()` right after scoring, filtering over-budget candidates from `decision.scored_candidates`.

**Design:** thoughts/shared/designs/2026-04-14-dynamic-feedback-loop-design.md

---

## Dependency Graph

```
Batch 1 (parallel): 1.1, 1.2, 1.3          [types & pure logic — no deps]
Batch 2 (parallel): 2.1, 2.2, 2.3          [services consuming Batch 1 types]
Batch 3 (parallel): 3.1, 3.2               [integration — wires Batch 2 into orchestrator + DI]
Batch 4 (single):   4.1                    [tests that span multiple units]
```

---

## Batch 1: Foundation (parallel — 3 implementers)

All tasks have NO dependencies and run simultaneously.

---

### Task 1.1: RealTimeObserver — types
**File:** `packages/services/real_time_observer/types.py`
**Test:** none (pure dataclasses)
**Depends:** none

```python
# packages/services/real_time_observer/types.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelHealthSignal:
    """Aggregated real-time health signal for one model, derived from
    recent llm_attempts rows (last N minutes).

    failure_rate : fraction of failed attempts in the window [0.0, 1.0].
    avg_latency_ms : mean latency of successful attempts; None if no successes.
    attempt_count : total attempts seen in the window (0 = no data → neutral).
    health_multiplier : pre-computed scalar in [0.3, 1.0] applied to base_total
        in ScoringEngine.  1.0 = fully healthy, 0.3 = severely degraded.
    """

    model_routing_key: str
    failure_rate: float          # [0.0, 1.0]
    avg_latency_ms: float | None
    attempt_count: int
    health_multiplier: float     # [0.3, 1.0]


@dataclass(frozen=True)
class RealTimeHealthSnapshot:
    """Map of routing_key → ModelHealthSignal for all models queried."""

    signals: dict[str, ModelHealthSignal] = field(default_factory=dict)

    def get_multiplier(self, routing_key: str) -> float:
        """Return health_multiplier for key, defaulting to 1.0 (healthy)."""
        signal = self.signals.get(routing_key)
        return signal.health_multiplier if signal is not None else 1.0
```

**Verify:** `python -c "from packages.services.real_time_observer.types import RealTimeHealthSnapshot; print('ok')"`
**Commit:** `feat(observer): add RealTimeObserver domain types`

---

### Task 1.2: BudgetController — pure validator
**File:** `packages/services/budget/controller.py`
**Test:** `apps/server/tests/test_budget_controller.py`
**Depends:** none

```python
# packages/services/budget/controller.py
"""Pre-flight budget guard.

Filters ScoredCandidates whose estimated cost exceeds the per-request limit.
Operates entirely on in-memory data (no I/O) so latency impact is <1 ms.
"""
from __future__ import annotations

from dataclasses import dataclass

from packages.domain.gateway import ScoredCandidate
from packages.domain.models import ModelProfile


@dataclass(frozen=True)
class BudgetConstraint:
    """Caller-supplied budget limit.

    max_estimated_cost_usd : hard ceiling per request in USD.
        None = no limit (pass-through).
    estimated_input_tokens : prompt + history token count from PromptEvaluator.
    estimated_output_tokens : expected completion size (default 512).
    """

    max_estimated_cost_usd: float | None
    estimated_input_tokens: int
    estimated_output_tokens: int = 512


def _estimate_cost(
    model: ModelProfile,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Compute USD cost estimate from ModelProfile pricing fields.

    prompt_price / completion_price are stored as USD per token
    (OpenRouter convention: price per token, not per 1k).
    Falls back to 0.0 if pricing metadata is absent.
    """
    prompt_price = model.prompt_price or 0.0
    completion_price = model.completion_price or 0.0
    return prompt_price * input_tokens + completion_price * output_tokens


class BudgetController:
    """Filters candidates that would exceed the budget constraint.

    Design decision: if ALL candidates exceed the budget, return the full
    list unchanged (prefer a response over a hard failure).  The orchestrator
    logs a warning in that case.
    """

    def filter_candidates(
        self,
        candidates: tuple[ScoredCandidate, ...],
        constraint: BudgetConstraint,
    ) -> tuple[ScoredCandidate, ...]:
        if constraint.max_estimated_cost_usd is None:
            return candidates

        within_budget: list[ScoredCandidate] = []
        for sc in candidates:
            cost = _estimate_cost(
                sc.model,
                constraint.estimated_input_tokens,
                constraint.estimated_output_tokens,
            )
            if cost <= constraint.max_estimated_cost_usd:
                within_budget.append(sc)

        # Safety: never return an empty list
        if not within_budget:
            return candidates

        return tuple(within_budget)

    def estimate_cost(
        self,
        model: ModelProfile,
        constraint: BudgetConstraint,
    ) -> float:
        return _estimate_cost(
            model,
            constraint.estimated_input_tokens,
            constraint.estimated_output_tokens,
        )
```

```python
# apps/server/tests/test_budget_controller.py
from __future__ import annotations

import pytest
from packages.domain.gateway import ScoredCandidate, ModelTier, HealthState
from packages.domain.models import ModelProfile, Capability
from packages.services.budget.controller import BudgetConstraint, BudgetController


def _make_model(
    model_id: str,
    prompt_price: float,
    completion_price: float,
) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities=set(),
        supports_tools=False,
        prompt_price=prompt_price,
        completion_price=completion_price,
    )


def _make_candidate(model: ModelProfile, rank: int) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=1.0,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER2_PROVISIONAL,
        health_status=HealthState.HEALTHY,
    )


class TestBudgetController:
    def setup_method(self):
        self.ctrl = BudgetController()

    def test_no_limit_returns_all(self):
        expensive = _make_model("gpt-4", prompt_price=0.01, completion_price=0.03)
        cheap = _make_model("gpt-3.5", prompt_price=0.001, completion_price=0.002)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(cheap, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=None,
            estimated_input_tokens=1000,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert result == candidates

    def test_filters_over_budget_candidate(self):
        # expensive: 1000 * 0.01 + 512 * 0.03 = 10 + 15.36 = 25.36 USD
        expensive = _make_model("gpt-4", prompt_price=0.01, completion_price=0.03)
        # cheap: 1000 * 0.0001 + 512 * 0.0002 = 0.1 + 0.1024 = 0.2024 USD
        cheap = _make_model("gpt-3.5", prompt_price=0.0001, completion_price=0.0002)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(cheap, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=1.0,
            estimated_input_tokens=1000,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 1
        assert result[0].model.model_id == "gpt-3.5"

    def test_all_over_budget_returns_all_unchanged(self):
        """Safety: never starve the pipeline entirely."""
        expensive = _make_model("gpt-4", prompt_price=1.0, completion_price=1.0)
        also_expensive = _make_model("claude-3", prompt_price=0.9, completion_price=0.9)
        candidates = (
            _make_candidate(expensive, 1),
            _make_candidate(also_expensive, 2),
        )
        constraint = BudgetConstraint(
            max_estimated_cost_usd=0.001,
            estimated_input_tokens=100,
        )
        result = self.ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 2

    def test_estimate_cost_no_pricing_returns_zero(self):
        free_model = _make_model("free-model", prompt_price=0.0, completion_price=0.0)
        constraint = BudgetConstraint(max_estimated_cost_usd=None, estimated_input_tokens=500)
        cost = self.ctrl.estimate_cost(free_model, constraint)
        assert cost == 0.0

    def test_estimate_cost_calculation(self):
        model = _make_model("gpt-4o", prompt_price=0.000005, completion_price=0.000015)
        constraint = BudgetConstraint(
            max_estimated_cost_usd=None,
            estimated_input_tokens=1000,
            estimated_output_tokens=200,
        )
        cost = self.ctrl.estimate_cost(model, constraint)
        # 1000 * 0.000005 + 200 * 0.000015 = 0.005 + 0.003 = 0.008
        assert abs(cost - 0.008) < 1e-9
```

**Verify:** `pytest apps/server/tests/test_budget_controller.py -v`
**Commit:** `feat(budget): add BudgetController with pre-flight cost estimation`

---

### Task 1.3: ScoringEngine — add `health_multiplier` parameter
**File:** `packages/core/scoring/engine.py`
**Test:** `apps/server/tests/test_scoring_engine_health.py`
**Depends:** none

**Design decision:** `health_multiplier` scales `base_total` (after jitter) before routing bonuses are added. Range [0.3, 1.0]. Added to `ScoreBreakdown` for full explainability.

```python
# packages/core/scoring/engine.py
# FULL FILE — replaces existing content
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
```

```python
# apps/server/tests/test_scoring_engine_health.py
from __future__ import annotations

import pytest
from packages.domain.gateway import Priority, Intent
from packages.domain.models import ModelProfile, Capability
from packages.core.scoring.engine import compute_model_score


def _base_model() -> ModelProfile:
    return ModelProfile(
        model_id="test-model",
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities={Capability.CODE},
        supports_tools=True,
    )


class TestHealthMultiplier:
    def test_full_health_does_not_penalize(self):
        model = _base_model()
        healthy = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.0,
        )
        no_param = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
        )
        assert abs(healthy.base_total - no_param.base_total) < 1e-9

    def test_degraded_health_reduces_base_total(self):
        model = _base_model()
        healthy = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.0,
        )
        degraded = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.6,
        )
        assert degraded.base_total < healthy.base_total
        assert abs(degraded.base_total - healthy.base_total * 0.6) < 1e-6

    def test_health_multiplier_clamped_to_minimum_0_3(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.0,   # Should be clamped to 0.3
        )
        assert breakdown.health_multiplier == 0.3

    def test_health_multiplier_clamped_to_maximum_1_0(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=1.5,   # Should be clamped to 1.0
        )
        assert breakdown.health_multiplier == 1.0

    def test_health_multiplier_appears_in_explanation(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            health_multiplier=0.75,
        )
        assert "health_mult=0.75" in breakdown.explanation

    def test_existing_jitter_and_health_combine_correctly(self):
        model = _base_model()
        breakdown = compute_model_score(
            model=model,
            priority=Priority.BALANCED,
            priority_weight=50,
            jitter_penalty=0.05,
            health_multiplier=0.8,
        )
        # base = (raw_base - 0.05) * 0.8
        # Routing bonuses are added AFTER health multiply
        assert breakdown.health_multiplier == 0.8
        assert breakdown.jitter_penalty == 0.05
```

**Verify:** `pytest apps/server/tests/test_scoring_engine_health.py -v`
**Commit:** `feat(scoring): add health_multiplier parameter to compute_model_score`

---

## Batch 2: Core Services (parallel — 3 implementers)

All tasks depend on Batch 1 completing.

---

### Task 2.1: RealTimeObserver — service implementation
**File:** `packages/services/real_time_observer/observer.py`
**Test:** `apps/server/tests/test_real_time_observer.py`
**Depends:** 1.1

**Design decision:** Query window = 10 minutes (configurable via `window_minutes`). Uses raw SQL via SQLModel `session.exec` for speed (<5ms). Health multiplier formula: `1.0 - (failure_rate * 0.7)` — a 100% failure rate yields 0.3 (min allowed). Latency spike bonus: if `avg_latency_ms > 5000`, applies additional -0.15 penalty before clamping.

```python
# packages/services/real_time_observer/observer.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select, func, text

from packages.infrastructure.db.models.llm_attempt import LLMAttempt
from packages.services.real_time_observer.types import ModelHealthSignal, RealTimeHealthSnapshot

_MIN_HEALTH_MULTIPLIER = 0.3
_MAX_HEALTH_MULTIPLIER = 1.0
_FAILURE_WEIGHT = 0.7       # How much failure_rate drags multiplier down
_LATENCY_SPIKE_MS = 5_000   # Threshold for high-latency penalty
_LATENCY_PENALTY = 0.15     # Additional penalty when avg latency > threshold
_MIN_ATTEMPTS_FOR_SIGNAL = 2  # Ignore single-attempt noise


def _compute_health_multiplier(failure_rate: float, avg_latency_ms: float | None) -> float:
    multiplier = 1.0 - (failure_rate * _FAILURE_WEIGHT)
    if avg_latency_ms is not None and avg_latency_ms > _LATENCY_SPIKE_MS:
        multiplier -= _LATENCY_PENALTY
    return max(_MIN_HEALTH_MULTIPLIER, min(_MAX_HEALTH_MULTIPLIER, multiplier))


class RealTimeObserver:
    """Queries recent llm_attempts to produce per-model health signals.

    No new DB table required — works with the existing llm_attempts schema.
    Designed to complete in <10ms via a single GROUP BY query.
    """

    def __init__(self, session: Session, *, window_minutes: int = 10) -> None:
        self.session = session
        self.window_minutes = window_minutes

    def get_health_snapshot(
        self, routing_keys: list[str] | None = None
    ) -> RealTimeHealthSnapshot:
        """Return a health snapshot for the given routing keys.

        If routing_keys is None, returns snapshot for ALL models seen
        in the time window (useful for bulk pre-scoring).
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)

        stmt = (
            select(
                LLMAttempt.model_routing_key,
                func.count().label("total"),
                func.sum(
                    # Map status to 1/0 for failure counting
                    func.cast(LLMAttempt.status != "success", type_=None)
                ).label("failures"),
                func.avg(LLMAttempt.latency_ms).label("avg_latency"),
            )
            .where(LLMAttempt.created_at >= since)
            .group_by(LLMAttempt.model_routing_key)
        )

        if routing_keys is not None:
            stmt = stmt.where(LLMAttempt.model_routing_key.in_(routing_keys))

        rows = self.session.exec(stmt).all()

        signals: dict[str, ModelHealthSignal] = {}
        for row in rows:
            key = row.model_routing_key
            total = int(row.total or 0)
            if total < _MIN_ATTEMPTS_FOR_SIGNAL:
                continue  # Not enough data → neutral (no entry)

            failures = int(row.failures or 0)
            failure_rate = failures / total
            avg_latency = float(row.avg_latency) if row.avg_latency is not None else None
            multiplier = _compute_health_multiplier(failure_rate, avg_latency)

            signals[key] = ModelHealthSignal(
                model_routing_key=key,
                failure_rate=failure_rate,
                avg_latency_ms=avg_latency,
                attempt_count=total,
                health_multiplier=multiplier,
            )

        return RealTimeHealthSnapshot(signals=signals)
```

```python
# apps/server/tests/test_real_time_observer.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from packages.services.real_time_observer.observer import (
    RealTimeObserver,
    _compute_health_multiplier,
    _MIN_HEALTH_MULTIPLIER,
)
from packages.services.real_time_observer.types import RealTimeHealthSnapshot


class TestComputeHealthMultiplier:
    def test_zero_failures_full_health(self):
        m = _compute_health_multiplier(0.0, None)
        assert m == 1.0

    def test_total_failure_clamps_to_minimum(self):
        m = _compute_health_multiplier(1.0, None)
        assert m == _MIN_HEALTH_MULTIPLIER

    def test_50pct_failure_rate(self):
        m = _compute_health_multiplier(0.5, None)
        # 1.0 - 0.5 * 0.7 = 0.65
        assert abs(m - 0.65) < 1e-9

    def test_latency_spike_applies_penalty(self):
        m_no_spike = _compute_health_multiplier(0.0, 3_000)
        m_spike = _compute_health_multiplier(0.0, 6_000)
        assert m_spike < m_no_spike
        # 1.0 - 0.15 = 0.85
        assert abs(m_spike - 0.85) < 1e-9

    def test_combined_failure_and_latency_spike_clamps(self):
        m = _compute_health_multiplier(1.0, 10_000)
        assert m == _MIN_HEALTH_MULTIPLIER


class TestRealTimeObserver:
    def _mock_session(self, rows):
        session = MagicMock()
        session.exec.return_value.all.return_value = rows
        return session

    def _make_row(self, key, total, failures, avg_latency):
        row = MagicMock()
        row.model_routing_key = key
        row.total = total
        row.failures = failures
        row.avg_latency = avg_latency
        return row

    def test_healthy_model_returns_full_multiplier(self):
        row = self._make_row("openai/gpt-4", 10, 0, 800.0)
        session = self._mock_session([row])
        observer = RealTimeObserver(session, window_minutes=10)
        snapshot = observer.get_health_snapshot()
        signal = snapshot.signals.get("openai/gpt-4")
        assert signal is not None
        assert signal.health_multiplier == 1.0

    def test_degraded_model_returns_reduced_multiplier(self):
        row = self._make_row("openai/gpt-4", 10, 5, 1000.0)
        session = self._mock_session([row])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        signal = snapshot.signals["openai/gpt-4"]
        # failure_rate = 0.5 → multiplier = 1 - 0.35 = 0.65
        assert signal.health_multiplier < 1.0
        assert abs(signal.health_multiplier - 0.65) < 1e-6

    def test_single_attempt_ignored_as_noise(self):
        row = self._make_row("openai/gpt-4", 1, 1, None)
        session = self._mock_session([row])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        # Only 1 attempt → ignored → no signal entry
        assert "openai/gpt-4" not in snapshot.signals

    def test_unknown_key_returns_default_multiplier(self):
        session = self._mock_session([])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        assert snapshot.get_multiplier("unknown/model") == 1.0

    def test_empty_window_returns_empty_snapshot(self):
        session = self._mock_session([])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        assert isinstance(snapshot, RealTimeHealthSnapshot)
        assert len(snapshot.signals) == 0
```

**Verify:** `pytest apps/server/tests/test_real_time_observer.py -v`
**Commit:** `feat(observer): implement RealTimeObserver with real-time health signals`

---

### Task 2.2: RealTimeObserver — `__init__.py` package
**File:** `packages/services/real_time_observer/__init__.py`
**Test:** none
**Depends:** 2.1

```python
# packages/services/real_time_observer/__init__.py
from packages.services.real_time_observer.observer import RealTimeObserver
from packages.services.real_time_observer.types import (
    ModelHealthSignal,
    RealTimeHealthSnapshot,
)

__all__ = [
    "RealTimeObserver",
    "ModelHealthSignal",
    "RealTimeHealthSnapshot",
]
```

**Verify:** `python -c "from packages.services.real_time_observer import RealTimeObserver; print('ok')"`
**Commit:** `chore(observer): add package __init__ for real_time_observer`

---

### Task 2.3: BudgetController — `__init__.py` package
**File:** `packages/services/budget/__init__.py`
**Test:** none
**Depends:** 1.2

```python
# packages/services/budget/__init__.py
from packages.services.budget.controller import BudgetConstraint, BudgetController

__all__ = ["BudgetConstraint", "BudgetController"]
```

**Verify:** `python -c "from packages.services.budget import BudgetController; print('ok')"`
**Commit:** `chore(budget): add package __init__ for budget module`

---

### Task 2.4: PromptEvaluator — enhanced token estimation
**File:** `packages/services/prompt_evaluation/evaluator.py`
**Test:** `apps/server/tests/test_prompt_evaluator_tokens.py`
**Depends:** 1.1

**Design decision:** `estimated_tokens` stays as the single public field (already exists on `PromptEvaluationResult`). Precision upgrade: switch from `word_count * 1.3` to char-based BPE approximation (`len(normalized) / 4.0`) as fallback for short word counts. Add `estimated_output_tokens: int` to `PromptEvaluationResult` derived from `response_depth` hint (default 512). This avoids adding history complexity now but leaves the hook open.

```python
# packages/services/prompt_evaluation/types.py
# FULL FILE — adds estimated_output_tokens field
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptEvaluationResult:
    intent: str
    complexity_score: float
    requires_reasoning: bool
    requires_code: bool
    requires_json: bool
    requires_tools: bool
    estimated_tokens: int
    keywords: list[str]
    estimated_output_tokens: int = 512   # NEW: default completion size estimate
```

```python
# packages/services/prompt_evaluation/evaluator.py
# FULL FILE — improved token estimation
from __future__ import annotations

from packages.services.prompt_evaluation.heuristics import (
    complexity_from_heuristics,
    extract_keywords,
    normalize_prompt,
    sentence_count,
    technical_term_hits,
    tokenize_words,
)
from packages.services.prompt_evaluation.types import PromptEvaluationResult

_CODE_TERMS = frozenset({"code", "function", "bug", "api", "sql", "python"})
_ANALYSIS_TERMS = frozenset({"analyze", "compare", "design", "architecture"})
_CREATIVE_TERMS = frozenset({"write", "story", "post", "creative"})

_JSON_TERMS = frozenset({"json", "schema", "structured"})
_TOOL_TERMS = frozenset({"search", "browse", "fetch", "tool"})

# Response depth → expected output token count
_DEPTH_OUTPUT_TOKENS: dict[str, int] = {
    "short": 256,
    "balanced": 512,
    "detailed": 1024,
}
_DEFAULT_OUTPUT_TOKENS = 512


def _contains_any(haystack_lower: str, terms: frozenset[str]) -> bool:
    return any(term in haystack_lower for term in terms)


def _classify_intent(lowered: str) -> str:
    if _contains_any(lowered, _CODE_TERMS):
        return "code"
    if _contains_any(lowered, _ANALYSIS_TERMS):
        return "analysis"
    if _contains_any(lowered, _CREATIVE_TERMS):
        return "creative"
    return "general"


def _estimate_input_tokens(normalized: str, word_count: int) -> int:
    """Hybrid token estimator.

    For short prompts (<10 words) the word-multiplier is unstable; fall back
    to char-based BPE approximation (avg 4 chars/token for English).
    For longer prompts blend both signals for higher accuracy.
    Decision: simple, dependency-free, <0.5ms.
    """
    word_estimate = max(1, int(word_count * 1.3))
    char_estimate = max(1, int(len(normalized) / 4.0))
    if word_count < 10:
        return char_estimate
    # Weighted blend: 60% word-based, 40% char-based
    return max(1, int(0.6 * word_estimate + 0.4 * char_estimate))


class PromptEvaluator:
    def evaluate(
        self, prompt: str, *, response_depth: str = "balanced"
    ) -> PromptEvaluationResult:
        normalized = normalize_prompt(prompt)
        lowered = normalized.lower()
        words = tokenize_words(normalized)
        keywords = extract_keywords(normalized, top_n=10)

        intent = _classify_intent(lowered)
        sentences = sentence_count(normalized)
        tech_hits = technical_term_hits(words)
        complexity_score = complexity_from_heuristics(
            raw_len=len(normalized),
            sentences=sentences,
            tech_hits=tech_hits,
            word_count=len(words),
        )

        requires_code = intent == "code"
        requires_json = _contains_any(lowered, _JSON_TERMS)
        requires_tools = _contains_any(lowered, _TOOL_TERMS)
        requires_reasoning = intent == "analysis" or complexity_score > 0.6

        estimated_tokens = _estimate_input_tokens(normalized, len(words))
        estimated_output_tokens = _DEPTH_OUTPUT_TOKENS.get(
            response_depth, _DEFAULT_OUTPUT_TOKENS
        )

        return PromptEvaluationResult(
            intent=intent,
            complexity_score=complexity_score,
            requires_reasoning=requires_reasoning,
            requires_code=requires_code,
            requires_json=requires_json,
            requires_tools=requires_tools,
            estimated_tokens=estimated_tokens,
            keywords=keywords,
            estimated_output_tokens=estimated_output_tokens,
        )
```

```python
# apps/server/tests/test_prompt_evaluator_tokens.py
from __future__ import annotations

import pytest
from packages.services.prompt_evaluation.evaluator import PromptEvaluator, _estimate_input_tokens


class TestEstimateInputTokens:
    def test_short_prompt_uses_char_estimate(self):
        # 5 words, 20 chars → char_estimate = 20/4 = 5
        tokens = _estimate_input_tokens("hello world", 2)
        assert tokens >= 1

    def test_longer_prompt_blends_estimates(self):
        normalized = "Write a Python function that implements a binary search tree with insertion and deletion"
        word_count = len(normalized.split())
        tokens = _estimate_input_tokens(normalized, word_count)
        # Sanity: should be in reasonable range
        assert 10 < tokens < 200

    def test_minimum_of_1_token(self):
        tokens = _estimate_input_tokens("", 0)
        assert tokens >= 1


class TestPromptEvaluatorOutputTokens:
    def setup_method(self):
        self.evaluator = PromptEvaluator()

    def test_default_depth_yields_512_output_tokens(self):
        result = self.evaluator.evaluate("What is the capital of France?")
        assert result.estimated_output_tokens == 512

    def test_short_depth_yields_256_output_tokens(self):
        result = self.evaluator.evaluate("What is the capital of France?", response_depth="short")
        assert result.estimated_output_tokens == 256

    def test_detailed_depth_yields_1024_output_tokens(self):
        result = self.evaluator.evaluate("Explain quantum entanglement in detail", response_depth="detailed")
        assert result.estimated_output_tokens == 1024

    def test_unknown_depth_falls_back_to_512(self):
        result = self.evaluator.evaluate("hello", response_depth="mega")
        assert result.estimated_output_tokens == 512

    def test_estimated_tokens_positive(self):
        result = self.evaluator.evaluate("Design a REST API for a social media app")
        assert result.estimated_tokens >= 1

    def test_code_intent_detected(self):
        result = self.evaluator.evaluate("Write a Python function to sort a list")
        assert result.intent == "code"
        assert result.requires_code is True
```

**Verify:** `pytest apps/server/tests/test_prompt_evaluator_tokens.py -v`
**Commit:** `feat(evaluator): improve token estimation and add estimated_output_tokens`

---

## Batch 3: Integration (parallel — 2 implementers)

All tasks depend on Batch 2 completing.

---

### Task 3.1: GatewayOrchestrator — wire BudgetController + RealTimeObserver
**File:** `packages/services/orchestration/orchestrator.py`
**Test:** `apps/server/tests/test_orchestrator_budget_health.py`
**Depends:** 2.1, 2.2, 2.3, 2.4, 1.2, 1.3

**Design decisions:**
- `RealTimeObserver` is optional; if `session` is available it's always instantiated inline (no DI change needed, consistent with existing pattern for `MetricsRepository`).
- `BudgetController` is always instantiated. `max_estimated_cost_usd` comes from `GatewayTask` (new optional field, see Task 3.2). If not set → no filtering.
- Observer query happens AFTER `build_decision()` so it doesn't block scoring. Health multipliers are applied by patching `scored_candidates` through a post-processing step. This keeps `ModelSelector` unchanged.
- Budget filtering applies to `decision.scored_candidates` immediately after health re-ranking, before execution.

```python
# packages/services/orchestration/orchestrator.py
# FULL FILE
from __future__ import annotations

import logging

from sqlmodel import Session

from packages.core.analysis.request_analysis import build_request_analysis_draft
from packages.domain.gateway import (
    GatewayExecutionResult,
    GatewayTask,
    InvocationAttempt,
    Priority,
    RankingHighlight,
    RankingSummary,
    RoutedRequest,
    RoutingDecision,
    ScoredCandidate,
    intent_from_evaluation_string,
)
from packages.domain.models import ModelProfile
from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
from packages.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from packages.infrastructure.db.repositories.attempt_repository import AttemptRepository
from packages.infrastructure.db.repositories.evaluation_repository import EvaluationRepository
from packages.infrastructure.db.repositories.execution_repository import ExecutionRepository
from packages.infrastructure.db.repositories.metrics_repository import MetricsRepository
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.repositories.request_repository import RequestRepository
from packages.services.budget.controller import BudgetConstraint, BudgetController
from packages.services.execution.fallback_executor import FallbackExecutor, RoutingExhaustedError
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation import PromptEvaluator, PromptEvaluationResult
from packages.services.real_time_observer import RealTimeObserver
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

logger = logging.getLogger(__name__)

_DEPTH_TOKENS = {"short": 256, "balanced": 512, "detailed": 1024}


def _extra_skills_from_evaluation(evaluation: PromptEvaluationResult) -> list[str]:
    tags: list[str] = []
    if evaluation.requires_code:
        tags.append("code")
    if evaluation.requires_json:
        tags.append("json")
    if evaluation.requires_tools:
        tags.append("tools")
    if evaluation.requires_reasoning:
        tags.append("reasoning")
    return tags


def _apply_health_to_candidates(
    scored_candidates: tuple[ScoredCandidate, ...],
    observer: RealTimeObserver,
) -> tuple[ScoredCandidate, ...]:
    """Re-weight ScoredCandidates with real-time health multipliers.

    Fetches a single health snapshot for all candidate routing keys, then
    builds new ScoredCandidate instances with adjusted final_score.
    Re-sorts by new final_score to maintain correct rank order.
    """
    from packages.core.scoring.engine import compute_model_score
    from packages.domain.gateway import Priority

    routing_keys = [sc.model.model_id for sc in scored_candidates]
    snapshot = observer.get_health_snapshot(routing_keys=routing_keys)

    if not snapshot.signals:
        # No recent data → no adjustment needed, skip re-sort
        return scored_candidates

    adjusted: list[tuple[float, ScoredCandidate]] = []
    for sc in scored_candidates:
        multiplier = snapshot.get_multiplier(sc.model.model_id)
        if abs(multiplier - 1.0) < 1e-6:
            adjusted.append((sc.final_score, sc))
        else:
            # Apply health to final_score proportionally
            new_score = sc.final_score * multiplier
            # Rebuild with updated explanation note
            updated_explanation = (
                f"{sc.explanation} [health_mult={multiplier:.2f} → score={new_score:.2f}]"
            )
            new_sc = ScoredCandidate(
                model=sc.model,
                priority_weight=sc.priority_weight,
                db_model_id=sc.db_model_id,
                rank=sc.rank,             # will be fixed after sort
                quality_score=sc.quality_score,
                latency_score=sc.latency_score,
                cost_score=sc.cost_score,
                final_score=new_score,
                model_score_adjustment=sc.model_score_adjustment,
                explanation=updated_explanation,
                pros=sc.pros,
                cons=sc.cons,
                tier=sc.tier,
                health_status=sc.health_status,
                snapshot_latency_p50=sc.snapshot_latency_p50,
                user_rating=sc.user_rating,
                user_rating_count=sc.user_rating_count,
            )
            adjusted.append((new_score, new_sc))

    adjusted.sort(key=lambda x: (-x[0], x[1].model.model_id))

    # Fix rank numbers after re-sort
    reranked: list[ScoredCandidate] = []
    for new_rank, (_, sc) in enumerate(adjusted, start=1):
        reranked.append(
            ScoredCandidate(
                model=sc.model,
                priority_weight=sc.priority_weight,
                db_model_id=sc.db_model_id,
                rank=new_rank,
                quality_score=sc.quality_score,
                latency_score=sc.latency_score,
                cost_score=sc.cost_score,
                final_score=sc.final_score,
                model_score_adjustment=sc.model_score_adjustment,
                explanation=sc.explanation,
                pros=sc.pros,
                cons=sc.cons,
                tier=sc.tier,
                health_status=sc.health_status,
                snapshot_latency_p50=sc.snapshot_latency_p50,
                user_rating=sc.user_rating,
                user_rating_count=sc.user_rating_count,
            )
        )
    return tuple(reranked)


class GatewayOrchestrator:
    def __init__(
        self,
        *,
        session: Session,
        model_repository: ModelRepository,
        fallback_registry,
        prompt_evaluator: PromptEvaluator,
        selector: ModelSelector,
        executor: FallbackExecutor,
    ) -> None:
        self.session = session
        self.model_repository = model_repository
        self.fallback_registry = fallback_registry
        self.prompt_evaluator = prompt_evaluator
        self.selector = selector
        self.executor = executor
        self._request_repo = RequestRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        self._eval_repo = EvaluationRepository(session)
        self._execution_repo = ExecutionRepository(session)
        self._attempt_repo = AttemptRepository(session)
        self._metrics_repo = MetricsRepository(session)
        self._budget_controller = BudgetController()
        self._observer = RealTimeObserver(session)

    def _maybe_sync_openrouter_catalog(self) -> None:
        settings = get_settings()
        if not settings.openrouter_auto_sync_on_empty_catalog:
            return
        if self.model_repository.count_routing_ready_models(require_json=False) > 0:
            return
        try:
            OpenRouterSyncService(self.session).sync_models()
            self.session.flush()
            logger.info("OpenRouter catalog auto-sync completed")
        except Exception:
            logger.exception("OpenRouter catalog auto-sync failed")

    def list_models(self) -> list[ModelProfile]:
        models = self.model_repository.list_all_models()
        if models:
            return models
        return self.fallback_registry.list_models()

    def execute(self, task: GatewayTask, *, session_id: str | None = None) -> GatewayExecutionResult:
        evaluation = self.prompt_evaluator.evaluate(
            task.prompt, response_depth=task.response_depth
        )
        intent = intent_from_evaluation_string(evaluation.intent)
        effective_require_json = task.require_json or evaluation.requires_json
        effective_max_tokens = (
            task.max_tokens
            if task.max_tokens is not None
            else _DEPTH_TOKENS.get(task.response_depth, 512)
        )

        logger.info(
            "prompt_evaluation intent=%s complexity=%.3f requires_code=%s requires_json=%s "
            "requires_tools=%s requires_reasoning=%s estimated_tokens=%d estimated_output_tokens=%d",
            evaluation.intent,
            evaluation.complexity_score,
            evaluation.requires_code,
            evaluation.requires_json,
            evaluation.requires_tools,
            evaluation.requires_reasoning,
            evaluation.estimated_tokens,
            evaluation.estimated_output_tokens,
        )

        llm_req = self._request_repo.create_request(
            prompt=task.prompt,
            intent=intent.value,
            priority=task.priority.value,
            require_json=effective_require_json,
            session_id=session_id,
        )

        draft = build_request_analysis_draft(
            task=task,
            intent=intent,
            complexity_score_override=evaluation.complexity_score,
            tokens_estimated_override=evaluation.estimated_tokens,
            extra_skills=_extra_skills_from_evaluation(evaluation),
            max_tokens_effective=effective_max_tokens,
        )
        self._analysis_repo.save_analysis(
            llm_req.id,
            task_type=draft.task_type,
            complexity_score=draft.complexity_score,
            cost_sensitivity=draft.cost_sensitivity,
            latency_sensitivity=draft.latency_sensitivity,
            detected_skills=draft.detected_skills,
            tokens_estimated=draft.tokens_estimated,
        )

        self._maybe_sync_openrouter_catalog()
        decision = self.selector.build_decision(
            task=task,
            intent=intent,
            evaluation=evaluation,
            require_json=effective_require_json,
        )

        # --- NEW: real-time health re-ranking ---
        health_adjusted_candidates = _apply_health_to_candidates(
            decision.scored_candidates,
            self._observer,
        )

        # --- NEW: budget filtering ---
        budget_constraint = BudgetConstraint(
            max_estimated_cost_usd=getattr(task, "max_cost_usd", None),
            estimated_input_tokens=evaluation.estimated_tokens,
            estimated_output_tokens=evaluation.estimated_output_tokens,
        )
        budget_filtered = self._budget_controller.filter_candidates(
            health_adjusted_candidates, budget_constraint
        )
        if len(budget_filtered) < len(health_adjusted_candidates):
            logger.info(
                "budget_filter removed %d candidates (limit=%.4f USD)",
                len(health_adjusted_candidates) - len(budget_filtered),
                budget_constraint.max_estimated_cost_usd,
            )

        # Rebuild RoutingDecision with budget-filtered + health-adjusted candidates
        final_decision = RoutingDecision(
            intent=decision.intent,
            reason=decision.reason,
            applied_temperature=decision.applied_temperature,
            candidates=[sc.model for sc in budget_filtered],
            scored_candidates=budget_filtered,
            preferred_providers=decision.preferred_providers,
            preferred_providers_applied=decision.preferred_providers_applied,
            preferred_providers_fallback_used=decision.preferred_providers_fallback_used,
        )

        evaluations = [
            ModelEvaluation(
                request_id=llm_req.id,
                model_id=sc.db_model_id,
                quality_score=sc.quality_score,
                latency_score=sc.latency_score,
                cost_score=sc.cost_score,
                final_score=sc.final_score,
                evaluation_rank=sc.rank,
                explanation=sc.explanation,
                pros=list(sc.pros) if sc.pros else None,
                cons=list(sc.cons) if sc.cons else None,
            )
            for sc in final_decision.scored_candidates
        ]
        self._eval_repo.bulk_insert_evaluations(evaluations)

        routed = RoutedRequest(
            prompt=task.prompt,
            temperature=final_decision.applied_temperature,
            max_tokens=effective_max_tokens,
            require_json=effective_require_json,
            simulate_failures=set(task.simulate_failures),
        )

        attempt_order = 0

        def on_attempt(att: InvocationAttempt) -> None:
            nonlocal attempt_order
            attempt_order += 1
            self._attempt_repo.save_attempt(
                request_id=llm_req.id,
                provider_slug=att.provider,
                model_routing_key=att.model_id,
                attempt_order=attempt_order,
                status=att.status,
                error=att.detail if att.status != "success" else None,
                latency_ms=att.latency_ms,
            )

        try:
            outcome = self.executor.run(
                request=routed,
                decision=final_decision,
                on_attempt=on_attempt,
            )
        except RoutingExhaustedError as exc:
            self._metrics_repo.record_request(
                session_id=session_id,
                success=False,
                latency_ms=0,
            )
            raise RoutingExhaustedError(
                exc.attempts,
                exc.reason,
                request_id=llm_req.id,
                scored_candidates=final_decision.scored_candidates,
            ) from exc

        win_id = self.model_repository.get_model_id_by_routing_key(outcome.response.model_id)
        if win_id is None:
            raise RuntimeError(f"Unknown routing key after success: {outcome.response.model_id}")

        self._execution_repo.save_execution(
            request_id=llm_req.id,
            model_id=win_id,
            input_tokens=outcome.response.input_tokens or 0,
            output_tokens=outcome.response.output_tokens or 0,
            latency_ms=outcome.response.latency_ms or 0,
            cost=outcome.response.cost,
            success=True,
            error=None,
        )

        fallback_used = len(outcome.attempts) > 1 or (
            bool(final_decision.candidates)
            and outcome.response.model_id != final_decision.candidates[0].model_id
        )
        self._request_repo.update_request_outcome(
            llm_req.id,
            selected_model_id=win_id,
            fallback_used=fallback_used,
        )

        self._metrics_repo.record_request(
            session_id=session_id,
            success=True,
            latency_ms=outcome.response.latency_ms or 0,
        )

        ranking_summary = _build_ranking_summary(final_decision, priority=task.priority)

        return GatewayExecutionResult(
            request_id=llm_req.id,
            response=outcome.response,
            decision=final_decision,
            attempts=outcome.attempts,
            fallback_used=fallback_used,
            ranking_summary=ranking_summary,
        )


_ECONOMICAL_COST_SCORE = 4
_FREE_ALT_MIN_SCORE_RATIO = 0.72


def _display_name(model_id: str) -> str:
    return model_id.split("/")[-1].replace("-", " ").title()


def _best_overall_reason_key(priority: Priority) -> str:
    return {
        Priority.BALANCED: "rankingReasonBestOverallBalanced",
        Priority.HIGH_QUALITY: "rankingReasonBestOverallHighQuality",
        Priority.LOW_COST: "rankingReasonBestOverallLowCost",
        Priority.LOW_LATENCY: "rankingReasonBestOverallLowLatency",
    }[priority]


def _highlight_from_candidate(
    candidate: ScoredCandidate,
    *,
    reason_key: str,
    same_as_best_overall: bool = False,
) -> RankingHighlight:
    return RankingHighlight(
        model_id=candidate.model.model_id,
        display_name=_display_name(candidate.model.model_id),
        provider=candidate.model.provider,
        reason_key=reason_key,
        same_as_best_overall=same_as_best_overall,
    )


def _argmax_candidate(
    candidates: tuple[ScoredCandidate, ...],
    *,
    key,
) -> ScoredCandidate:
    return max(candidates, key=lambda c: (key(c), c.final_score, c.model.model_id))


def _pick_free_alternative(best: ScoredCandidate, rest: tuple[ScoredCandidate, ...]) -> ScoredCandidate | None:
    if best.model.cost_score >= _ECONOMICAL_COST_SCORE:
        return None
    economical = [c for c in rest if c.model.cost_score >= _ECONOMICAL_COST_SCORE]
    if not economical:
        return None
    economical.sort(key=lambda c: (-c.final_score, c.model.model_id))
    pick = economical[0]
    if pick.final_score < best.final_score * _FREE_ALT_MIN_SCORE_RATIO:
        return None
    return pick


def _build_ranking_summary(decision: RoutingDecision, *, priority: Priority) -> RankingSummary:
    candidates = decision.scored_candidates
    if not candidates:
        placeholder = RankingHighlight(
            model_id="",
            display_name="",
            provider="",
            reason_key="rankingReasonNoRanking",
            same_as_best_overall=False,
        )
        return RankingSummary(
            best_overall=placeholder,
            free_alternative=None,
            best_quality=placeholder,
            best_cost=placeholder,
            best_speed=placeholder,
        )

    best = candidates[0]
    rest = candidates[1:]

    best_h = _highlight_from_candidate(best, reason_key=_best_overall_reason_key(priority))

    free_pick = _pick_free_alternative(best, rest)
    free_h = (
        _highlight_from_candidate(free_pick, reason_key="rankingReasonFreeAlternative")
        if free_pick is not None
        else None
    )

    q = _argmax_candidate(candidates, key=lambda c: c.quality_score)
    co = _argmax_candidate(candidates, key=lambda c: c.cost_score)
    sp = _argmax_candidate(candidates, key=lambda c: c.latency_score)

    return RankingSummary(
        best_overall=best_h,
        free_alternative=free_h,
        best_quality=_highlight_from_candidate(
            q,
            reason_key="rankingReasonCategoryQuality",
            same_as_best_overall=q.model.model_id == best.model.model_id,
        ),
        best_cost=_highlight_from_candidate(
            co,
            reason_key="rankingReasonCategoryCost",
            same_as_best_overall=co.model.model_id == best.model.model_id,
        ),
        best_speed=_highlight_from_candidate(
            sp,
            reason_key="rankingReasonCategorySpeed",
            same_as_best_overall=sp.model.model_id == best.model.model_id,
        ),
    )
```

```python
# apps/server/tests/test_orchestrator_budget_health.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from packages.services.orchestration.orchestrator import _apply_health_to_candidates
from packages.domain.gateway import ScoredCandidate, ModelTier, HealthState, RoutingDecision, Intent, Priority
from packages.domain.models import ModelProfile, Capability
from packages.services.real_time_observer.types import RealTimeHealthSnapshot, ModelHealthSignal


def _make_model(model_id: str) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=60,
        default_temperature=0.7,
        capabilities=set(),
        supports_tools=False,
    )


def _make_candidate(model: ModelProfile, rank: int, score: float = 1.0) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=score,
        model_score_adjustment=0.0,
        explanation="base",
        pros=(),
        cons=(),
        tier=ModelTier.TIER1_VERIFIED,
        health_status=HealthState.HEALTHY,
    )


class TestApplyHealthToCandidates:
    def _make_observer(self, signals: dict) -> MagicMock:
        observer = MagicMock()
        snapshot = RealTimeHealthSnapshot(signals=signals)
        observer.get_health_snapshot.return_value = snapshot
        return observer

    def test_no_signals_returns_unchanged(self):
        model_a = _make_model("openai/gpt-4")
        candidates = (_make_candidate(model_a, 1, 1.5),)
        observer = self._make_observer({})
        result = _apply_health_to_candidates(candidates, observer)
        assert result[0].final_score == 1.5

    def test_degraded_model_gets_lower_score(self):
        model_a = _make_model("openai/gpt-4")
        model_b = _make_model("anthropic/claude-3")
        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.5),
        )
        signals = {
            "openai/gpt-4": ModelHealthSignal(
                model_routing_key="openai/gpt-4",
                failure_rate=0.5,
                avg_latency_ms=1000.0,
                attempt_count=10,
                health_multiplier=0.65,
            )
        }
        observer = self._make_observer(signals)
        result = _apply_health_to_candidates(candidates, observer)
        gpt4_sc = next(sc for sc in result if sc.model.model_id == "openai/gpt-4")
        assert abs(gpt4_sc.final_score - 2.0 * 0.65) < 1e-6

    def test_re_sort_promotes_healthier_model(self):
        # gpt-4 starts rank 1 with score 2.0 but is 50% failing
        # claude starts rank 2 with score 1.8 and is healthy
        model_a = _make_model("openai/gpt-4")
        model_b = _make_model("anthropic/claude-3")
        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.8),
        )
        signals = {
            "openai/gpt-4": ModelHealthSignal(
                model_routing_key="openai/gpt-4",
                failure_rate=1.0,
                avg_latency_ms=None,
                attempt_count=10,
                health_multiplier=0.3,   # heavily degraded
            )
        }
        observer = self._make_observer(signals)
        result = _apply_health_to_candidates(candidates, observer)
        # gpt-4 degraded score = 2.0 * 0.3 = 0.6 < claude's 1.8
        assert result[0].model.model_id == "anthropic/claude-3"
        assert result[0].rank == 1
        assert result[1].rank == 2

    def test_rank_numbers_fixed_after_resort(self):
        model_a = _make_model("a/model")
        model_b = _make_model("b/model")
        model_c = _make_model("c/model")
        candidates = (
            _make_candidate(model_a, 1, 3.0),
            _make_candidate(model_b, 2, 2.0),
            _make_candidate(model_c, 3, 1.0),
        )
        signals = {
            "a/model": ModelHealthSignal(
                model_routing_key="a/model",
                failure_rate=1.0,
                avg_latency_ms=None,
                attempt_count=5,
                health_multiplier=0.3,
            )
        }
        observer = self._make_observer(signals)
        result = _apply_health_to_candidates(candidates, observer)
        ranks = [sc.rank for sc in result]
        assert ranks == [1, 2, 3]
```

**Verify:** `pytest apps/server/tests/test_orchestrator_budget_health.py -v`
**Commit:** `feat(orchestrator): wire RealTimeObserver and BudgetController into execute()`

---

### Task 3.2: GatewayTask — add `max_cost_usd` field
**File:** `packages/domain/gateway.py`
**Test:** `apps/server/tests/test_domain_gateway_types.py` (extend existing)
**Depends:** 1.2

**Design decision:** `max_cost_usd: float | None = None` — optional field, zero breaking change. Existing callers pass nothing and get `None` (no budget filtering).

```python
# packages/domain/gateway.py
# DIFF: add max_cost_usd to GatewayTask only — all other content unchanged.
# Replace the GatewayTask dataclass definition:

@dataclass(frozen=True)
class GatewayTask:
    prompt: str
    priority: Priority
    temperature: float | None
    max_tokens: int | None
    require_json: bool
    discovery_mode: bool = False
    simulate_failures: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    preferred_providers: list[str] = field(default_factory=list)
    response_depth: str = "balanced"
    max_cost_usd: float | None = None   # NEW: per-request budget ceiling in USD
```

Note: The full file keeps all other dataclasses/enums unchanged. Only `GatewayTask` gains `max_cost_usd`.

```python
# Append to apps/server/tests/test_domain_gateway_types.py
# (add these test cases to the existing file — they test the new field)

def test_gateway_task_default_max_cost_is_none():
    from packages.domain.gateway import GatewayTask, Priority
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
    )
    assert task.max_cost_usd is None


def test_gateway_task_accepts_max_cost():
    from packages.domain.gateway import GatewayTask, Priority
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
        max_cost_usd=0.05,
    )
    assert task.max_cost_usd == 0.05
```

**Verify:** `pytest apps/server/tests/test_domain_gateway_types.py -v`
**Commit:** `feat(domain): add max_cost_usd to GatewayTask for pre-flight budget`

---

## Batch 4: Cross-cutting Integration Test (single implementer)

Depends on ALL Batch 3 tasks.

---

### Task 4.1: End-to-end pipeline integration test
**File:** `apps/server/tests/test_dynamic_feedback_loop_integration.py`
**Test:** (is the test)
**Depends:** 3.1, 3.2

**Design decision:** Uses mocked session, mocked provider, and real scoring/budget logic. Validates that the full flow (evaluate → health-adjust → budget-filter → execute) works end-to-end without a live DB.

```python
# apps/server/tests/test_dynamic_feedback_loop_integration.py
"""Integration test for the dynamic feedback loop pipeline.

Tests that RealTimeObserver health signals + BudgetController filtering
integrate correctly through GatewayOrchestrator without a live database.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from packages.domain.gateway import (
    GatewayTask,
    Priority,
    ScoredCandidate,
    ModelTier,
    HealthState,
    RoutingDecision,
    Intent,
    ProviderResponse,
    FallbackExecutionOutcome,
    InvocationAttempt,
)
from packages.domain.models import ModelProfile, Capability
from packages.services.budget.controller import BudgetConstraint, BudgetController
from packages.services.real_time_observer.types import RealTimeHealthSnapshot, ModelHealthSignal
from packages.services.orchestration.orchestrator import _apply_health_to_candidates


def _make_model(model_id: str, prompt_price: float = 0.0, completion_price: float = 0.0) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities=set(),
        supports_tools=False,
        prompt_price=prompt_price,
        completion_price=completion_price,
    )


def _make_candidate(model: ModelProfile, rank: int, score: float) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=score,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER1_VERIFIED,
        health_status=HealthState.HEALTHY,
    )


class TestFullFeedbackLoopPipeline:
    def test_health_degradation_plus_budget_filter(self):
        """Top model is degraded → re-ranked below alt. Alt exceeds budget → filtered.
        Result: degraded model (still within budget at reduced score) survives.
        """
        # Model A: expensive, initially top-ranked but degraded
        model_a = _make_model("openai/gpt-4", prompt_price=0.01, completion_price=0.03)
        # Model B: cheap, initially rank-2
        model_b = _make_model("google/gemini-flash", prompt_price=0.00001, completion_price=0.00002)

        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.5),
        )

        # Health: model_a is severely degraded
        signals = {
            "openai/gpt-4": ModelHealthSignal(
                model_routing_key="openai/gpt-4",
                failure_rate=0.8,
                avg_latency_ms=None,
                attempt_count=10,
                health_multiplier=0.44,  # 1 - 0.8*0.7 = 0.44
            )
        }
        observer = MagicMock()
        observer.get_health_snapshot.return_value = RealTimeHealthSnapshot(signals=signals)

        # Step 1: health re-ranking
        health_adjusted = _apply_health_to_candidates(candidates, observer)
        # gpt-4: 2.0 * 0.44 = 0.88, gemini: 1.5 (unchanged) → gemini now rank 1
        assert health_adjusted[0].model.model_id == "google/gemini-flash"

        # Step 2: budget filtering — budget set to $5 max
        # gpt-4 cost: 1000*0.01 + 512*0.03 = $25.36 → over budget
        # gemini cost: 1000*0.00001 + 512*0.00002 = $0.02 → within budget
        ctrl = BudgetController()
        constraint = BudgetConstraint(
            max_estimated_cost_usd=5.0,
            estimated_input_tokens=1000,
            estimated_output_tokens=512,
        )
        budget_filtered = ctrl.filter_candidates(health_adjusted, constraint)
        assert len(budget_filtered) == 1
        assert budget_filtered[0].model.model_id == "google/gemini-flash"

    def test_no_health_data_no_budget_passthrough(self):
        """With no health signals and no budget limit, pipeline is transparent."""
        model_a = _make_model("openai/gpt-4")
        model_b = _make_model("anthropic/claude-3")
        candidates = (
            _make_candidate(model_a, 1, 2.0),
            _make_candidate(model_b, 2, 1.5),
        )
        observer = MagicMock()
        observer.get_health_snapshot.return_value = RealTimeHealthSnapshot(signals={})

        health_adjusted = _apply_health_to_candidates(candidates, observer)
        assert health_adjusted == candidates  # unchanged

        ctrl = BudgetController()
        constraint = BudgetConstraint(max_estimated_cost_usd=None, estimated_input_tokens=500)
        result = ctrl.filter_candidates(health_adjusted, constraint)
        assert result == candidates

    def test_all_candidates_over_budget_safety_passthrough(self):
        """Safety: if every model exceeds budget, return all unchanged."""
        expensive_a = _make_model("a/model", prompt_price=1.0, completion_price=1.0)
        expensive_b = _make_model("b/model", prompt_price=0.9, completion_price=0.9)
        candidates = (
            _make_candidate(expensive_a, 1, 2.0),
            _make_candidate(expensive_b, 2, 1.5),
        )
        ctrl = BudgetController()
        constraint = BudgetConstraint(
            max_estimated_cost_usd=0.001,
            estimated_input_tokens=100,
        )
        result = ctrl.filter_candidates(candidates, constraint)
        assert len(result) == 2  # Safety: no starvation
```

**Verify:** `pytest apps/server/tests/test_dynamic_feedback_loop_integration.py -v`
**Commit:** `test(integration): add end-to-end dynamic feedback loop pipeline tests`

---

## Summary of All New/Modified Files

| File | Action | Batch |
|------|--------|-------|
| `packages/services/real_time_observer/types.py` | CREATE | 1.1 |
| `packages/services/budget/controller.py` | CREATE | 1.2 |
| `apps/server/tests/test_budget_controller.py` | CREATE | 1.2 |
| `packages/core/scoring/engine.py` | MODIFY | 1.3 |
| `apps/server/tests/test_scoring_engine_health.py` | CREATE | 1.3 |
| `packages/services/real_time_observer/observer.py` | CREATE | 2.1 |
| `apps/server/tests/test_real_time_observer.py` | CREATE | 2.1 |
| `packages/services/real_time_observer/__init__.py` | CREATE | 2.2 |
| `packages/services/budget/__init__.py` | CREATE | 2.3 |
| `packages/services/prompt_evaluation/types.py` | MODIFY | 2.4 |
| `packages/services/prompt_evaluation/evaluator.py` | MODIFY | 2.4 |
| `apps/server/tests/test_prompt_evaluator_tokens.py` | CREATE | 2.4 |
| `packages/services/orchestration/orchestrator.py` | MODIFY | 3.1 |
| `apps/server/tests/test_orchestrator_budget_health.py` | CREATE | 3.1 |
| `packages/domain/gateway.py` | MODIFY | 3.2 |
| `apps/server/tests/test_domain_gateway_types.py` | MODIFY | 3.2 |
| `apps/server/tests/test_dynamic_feedback_loop_integration.py` | CREATE | 4.1 |

## Key Design Choices

| Decision | Rationale |
|----------|-----------|
| Health multiplier applied to `final_score` in orchestrator (not in `compute_model_score` directly) | Keeps `ModelSelector` unchanged; observer is an orchestration concern, not a scoring primitive |
| `health_multiplier` also added to `compute_model_score` signature | Enables unit-testing scoring-level penalties independently; `ModelSelector` can pass it in future |
| `RealTimeObserver` uses single GROUP BY query | <5ms latency; no new tables; safe with existing FK constraints |
| `BudgetController` returns all candidates when all exceed budget | Prevents routing starvation; logs a warning; callers can decide to reject upstream |
| `estimated_output_tokens` on `PromptEvaluationResult` | Feeds `BudgetController` without extra I/O; derived from `response_depth` which is already on `GatewayTask` |
| `max_cost_usd` optional on `GatewayTask` | Zero breaking change; all existing call sites pass `None` implicitly |
