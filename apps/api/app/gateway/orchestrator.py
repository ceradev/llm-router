from __future__ import annotations

from app.catalog.registry import ModelRegistry
from app.catalog.types import ModelProfile
from app.gateway.classify import PromptClassifier
from app.gateway.fallback import FallbackExecutor
from app.gateway.select import ModelSelector
from app.gateway.types import GatewayExecutionResult, GatewayTask, RoutedRequest


class GatewayOrchestrator:
    def __init__(
        self,
        *,
        registry: ModelRegistry,
        classifier: PromptClassifier,
        selector: ModelSelector,
        executor: FallbackExecutor,
    ) -> None:
        self.registry = registry
        self.classifier = classifier
        self.selector = selector
        self.executor = executor

    def list_models(self) -> list[ModelProfile]:
        return self.registry.list_models()

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
