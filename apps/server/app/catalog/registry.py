from __future__ import annotations

from app.catalog.catalog import list_models
from app.catalog.types import ModelProfile


class ModelRegistry:
    def __init__(self) -> None:
        self._models = {
            model.model_id: model
            for model in self._load_models()
        }

    def _load_models(self) -> list[ModelProfile]:
        return list_models()

    def list_models(self) -> list[ModelProfile]:
        return list(self._models.values())

    def get(self, model_id: str) -> ModelProfile:
        return self._models[model_id]
