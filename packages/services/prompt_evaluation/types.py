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
