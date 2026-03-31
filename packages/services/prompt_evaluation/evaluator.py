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


class PromptEvaluator:
    def evaluate(self, prompt: str) -> PromptEvaluationResult:
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

        word_count = len(words)
        estimated_tokens = max(1, int(word_count * 1.3))

        return PromptEvaluationResult(
            intent=intent,
            complexity_score=complexity_score,
            requires_reasoning=requires_reasoning,
            requires_code=requires_code,
            requires_json=requires_json,
            requires_tools=requires_tools,
            estimated_tokens=estimated_tokens,
            keywords=keywords,
        )
