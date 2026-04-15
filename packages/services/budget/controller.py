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
