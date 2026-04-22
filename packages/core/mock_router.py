"""Mock routing logic used by the local CLI.

This module intentionally lives in `packages/core` so the CLI can consume
domain-like logic directly without going through HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    provider: str
    capability: str
    estimated_cost: str
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class Decision:
    prompt: str
    recommended: Candidate
    alternatives: list[Candidate]


def _prompt_traits(prompt: str) -> dict[str, bool]:
    normalized = prompt.lower()
    return {
        "is_refactor": any(word in normalized for word in ("refactor", "architecture", "cleanup")),
        "is_creative": any(word in normalized for word in ("brainstorm", "creative", "copywriting")),
        "is_fast": any(word in normalized for word in ("quick", "fast", "short", "tl;dr")),
        "is_code": any(word in normalized for word in ("python", "typescript", "bug", "endpoint", "api")),
    }


def get_candidates(prompt: str) -> list[Candidate]:
    """Return realistic mock candidates for a prompt."""
    traits = _prompt_traits(prompt)

    candidates = [
        Candidate(
            name="claude-3.7-sonnet",
            provider="Anthropic",
            capability="excellent_reasoning",
            estimated_cost="$$",
            score=0.86,
            reasons=["Strong architecture understanding", "Reliable long-context behavior"],
        ),
        Candidate(
            name="gpt-4.1",
            provider="OpenAI",
            capability="balanced_general",
            estimated_cost="$$$",
            score=0.82,
            reasons=["High quality for coding tasks", "Consistent instruction following"],
        ),
        Candidate(
            name="gemini-2.5-pro",
            provider="Google",
            capability="long_context",
            estimated_cost="$$",
            score=0.79,
            reasons=["Good with multi-file reasoning", "Competitive quality/cost ratio"],
        ),
        Candidate(
            name="llama-3.3-70b",
            provider="Groq",
            capability="fast_cost_effective",
            estimated_cost="$",
            score=0.74,
            reasons=["Low latency for iterative workflows", "Lower inference cost"],
        ),
    ]

    adjusted: list[Candidate] = []
    for candidate in candidates:
        score = candidate.score
        reasons = list(candidate.reasons)

        if traits["is_refactor"] and "reasoning" in candidate.capability:
            score += 0.05
            reasons.append("Boosted for refactor/architecture workload")
        if traits["is_code"] and "coding" in " ".join(reasons).lower():
            score += 0.03
            reasons.append("Boosted for code-heavy prompt")
        if traits["is_fast"] and "fast" in candidate.capability:
            score += 0.08
            reasons.append("Boosted for low-latency intent")
        if traits["is_creative"] and "balanced" in candidate.capability:
            score += 0.04
            reasons.append("Boosted for creative and open-ended generation")

        adjusted.append(
            Candidate(
                name=candidate.name,
                provider=candidate.provider,
                capability=candidate.capability,
                estimated_cost=candidate.estimated_cost,
                score=round(min(score, 0.99), 3),
                reasons=reasons,
            )
        )

    return adjusted


def rank_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """Sort candidates by descending score."""
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def build_decision(prompt: str) -> Decision:
    """Build a mock decision object from a prompt."""
    ranked = rank_candidates(get_candidates(prompt))
    recommended = ranked[0]
    alternatives = ranked[1:3]
    return Decision(prompt=prompt, recommended=recommended, alternatives=alternatives)


def list_available_models() -> list[Candidate]:
    """Return a static model catalog for the `models` command."""
    return rank_candidates(get_candidates("general coding task"))
