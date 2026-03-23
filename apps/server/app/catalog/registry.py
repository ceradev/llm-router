from __future__ import annotations

from app.catalog.types import ModelProfile
from app.providers.anthropic.catalog import list_models as list_anthropic_models
from app.providers.deepseek.catalog import list_models as list_deepseek_models
from app.providers.groq.catalog import list_models as list_groq_models
from app.providers.openai.catalog import list_models as list_openai_models


class ModelRegistry:
    def __init__(self) -> None:
        self._models = {
            model.model_id: model
            for model in self._load_models()
        }

    def _load_models(self) -> list[ModelProfile]:
        return [
            *list_openai_models(),
            *list_anthropic_models(),
            *list_groq_models(),
            *list_deepseek_models(),
        ]

    def list_models(self) -> list[ModelProfile]:
        return list(self._models.values())

    def get(self, model_id: str) -> ModelProfile:
        return self._models[model_id]
