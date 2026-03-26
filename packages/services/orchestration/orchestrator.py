from __future__ import annotations

from packages.core.classification.prompt_classifier import PromptClassifier
from packages.domain.gateway import GatewayExecutionResult, GatewayTask, RoutedRequest
from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.services.model_selection.service import ModelSelector


class GatewayOrchestrator:
    def __init__(
        self,
        *,
        model_repository: ModelRepository,
        fallback_registry,
        classifier: PromptClassifier,
        selector: ModelSelector,
        executor: FallbackExecutor,
    ) -> None:
        self.model_repository = model_repository
        self.fallback_registry = fallback_registry
        self.classifier = classifier
        self.selector = selector
        self.executor = executor

    def list_models(self) -> list[ModelProfile]:
        models = self.model_repository.list_all_models()
        if models:
            return models
        return self.fallback_registry.list_models()

    def execute(self, task: GatewayTask) -> GatewayExecutionResult:
        intent = self.classifier.detect(task.prompt)
        decision = self.selector.build_decision(task=task, intent=intent)
        request = RoutedRequest(
            prompt=task.prompt,
            temperature=decision.applied_temperature,
            max_tokens=task.max_tokens,
            require_json=task.require_json,
            simulate_failures=set(task.simulate_failures),
        )
        return self.executor.run(request=request, decision=decision)

