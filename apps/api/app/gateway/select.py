from __future__ import annotations

from app.catalog.registry import ModelRegistry
from app.catalog.types import ModelProfile
from app.gateway.types import GatewayTask, Intent, Priority, RoutingDecision


class ModelSelector:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def build_decision(self, *, task: GatewayTask, intent: Intent) -> RoutingDecision:
        candidate_ids = self._candidate_ids(intent=intent, priority=task.priority)
        candidates = [self.registry.get(model_id) for model_id in candidate_ids]

        if task.require_json:
            candidates = [model for model in candidates if model.supports_json]

        if not candidates:
            candidates = [
                model
                for model in self.registry.list_models()
                if not task.require_json or model.supports_json
            ]

        temperature = task.temperature
        if temperature is None:
            temperature = self._default_temperature(intent, candidates[0])

        return RoutingDecision(
            intent=intent,
            reason=self._build_reason(
                intent=intent,
                priority=task.priority.value,
                primary_model=candidates[0].model_id,
                require_json=task.require_json,
            ),
            applied_temperature=temperature,
            candidates=candidates,
        )

    def _candidate_ids(self, *, intent: Intent, priority: Priority) -> list[str]:
        by_intent: dict[Intent, list[str]] = {
            Intent.CODE: [
                "deepseek/gateway-code",
                "openai/gateway-fast",
                "anthropic/gateway-quality",
            ],
            Intent.ANALYSIS: [
                "anthropic/gateway-quality",
                "openai/gateway-fast",
                "groq/gateway-low-latency",
            ],
            Intent.CREATIVE: [
                "anthropic/gateway-quality",
                "openai/gateway-fast",
                "groq/gateway-low-latency",
            ],
            Intent.GENERAL: [
                "openai/gateway-fast",
                "groq/gateway-low-latency",
                "anthropic/gateway-quality",
            ],
        }
        by_priority: dict[Priority, list[str]] = {
            Priority.BALANCED: [
                "openai/gateway-fast",
                "anthropic/gateway-quality",
                "groq/gateway-low-latency",
                "deepseek/gateway-code",
            ],
            Priority.LOW_COST: [
                "groq/gateway-low-latency",
                "deepseek/gateway-code",
                "openai/gateway-fast",
                "anthropic/gateway-quality",
            ],
            Priority.HIGH_QUALITY: [
                "anthropic/gateway-quality",
                "deepseek/gateway-code",
                "openai/gateway-fast",
                "groq/gateway-low-latency",
            ],
            Priority.LOW_LATENCY: [
                "groq/gateway-low-latency",
                "openai/gateway-fast",
                "deepseek/gateway-code",
                "anthropic/gateway-quality",
            ],
        }

        ordered_ids: list[str] = []
        for source in (by_intent[intent], by_priority[priority]):
            for model_id in source:
                if model_id not in ordered_ids:
                    ordered_ids.append(model_id)
        return ordered_ids

    def _default_temperature(self, intent: Intent, primary_model: ModelProfile) -> float:
        if intent == Intent.CODE:
            return 0.1
        if intent == Intent.CREATIVE:
            return 0.8
        if intent == Intent.ANALYSIS:
            return 0.2
        return primary_model.default_temperature

    def _build_reason(
        self,
        *,
        intent: Intent,
        priority: str,
        primary_model: str,
        require_json: bool,
    ) -> str:
        reason = (
            f"Intent detected: {intent.value}. Priority: {priority}. "
            f"Primary candidate: {primary_model}."
        )
        if require_json:
            reason += " JSON-capable models only."
        return reason
