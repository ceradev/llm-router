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
