from __future__ import annotations

from app.gateway.types import (
    GatewayExecutionResult,
    InvocationAttempt,
    RoutedRequest,
    RoutingDecision,
)
from app.providers.base import ProviderAdapter, ProviderError


class RoutingExhaustedError(RuntimeError):
    def __init__(self, attempts: list[InvocationAttempt], reason: str) -> None:
        super().__init__("All routing candidates failed")
        self.attempts = attempts
        self.reason = reason


class FallbackExecutor:
    def __init__(self, providers: dict[str, ProviderAdapter]) -> None:
        self.providers = providers

    def run(
        self,
        *,
        request: RoutedRequest,
        decision: RoutingDecision,
    ) -> GatewayExecutionResult:
        attempts: list[InvocationAttempt] = []

        for model in decision.candidates:
            provider = self.providers[model.provider]
            try:
                response = provider.generate(request, model)
                attempts.append(
                    InvocationAttempt(
                        provider=model.provider,
                        model_id=model.model_id,
                        status="success",
                        detail="Request completed",
                    )
                )
                return GatewayExecutionResult(
                    response=response,
                    decision=decision,
                    attempts=attempts,
                )
            except ProviderError as exc:
                attempts.append(
                    InvocationAttempt(
                        provider=model.provider,
                        model_id=model.model_id,
                        status="failed",
                        detail=str(exc),
                    )
                )

        raise RoutingExhaustedError(attempts=attempts, reason=decision.reason)
