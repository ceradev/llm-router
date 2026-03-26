from __future__ import annotations

from packages.domain.gateway import Intent

CODE_HINTS = {
    "api",
    "bug",
    "codigo",
    "code",
    "depura",
    "debug",
    "function",
    "python",
    "refactoriza",
    "refactor",
    "sql",
    "test",
}

ANALYSIS_HINTS = {
    "analyze",
    "analiza",
    "architecture",
    "arquitectura",
    "compare",
    "compara",
    "design",
    "disena",
    "diseña",
    "evaluate",
    "evalua",
    "evalúa",
    "plan",
    "reason",
    "tradeoff",
}

CREATIVE_HINTS = {
    "ad",
    "brand",
    "campaign",
    "creative",
    "creativa",
    "poem",
    "post",
    "script",
    "story",
}


class PromptClassifier:
    def detect(self, prompt: str) -> Intent:
        lowered = prompt.lower()
        if any(term in lowered for term in CODE_HINTS):
            return Intent.CODE
        if any(term in lowered for term in CREATIVE_HINTS):
            return Intent.CREATIVE
        if any(term in lowered for term in ANALYSIS_HINTS) or len(prompt) > 700:
            return Intent.ANALYSIS
        return Intent.GENERAL

