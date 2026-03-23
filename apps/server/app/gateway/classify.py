from __future__ import annotations

from app.gateway.types import Intent

# This is a very naive implementation of a prompt classifier. It simply checks for the presence of certain keywords in the prompt to determine the intent.
# In a real implementation, you would likely want to use a more sophisticated approach, such as training a machine learning model on a dataset of labeled prompts.
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
