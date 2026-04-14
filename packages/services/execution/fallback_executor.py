from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from packages.domain.gateway import (
    FallbackExecutionOutcome,
    InvocationAttempt,
    RoutedRequest,
    RoutingDecision,
    ScoredCandidate,
)
from packages.infrastructure.providers.base import ProviderAdapter, ProviderError

if TYPE_CHECKING:
    from packages.infrastructure.db.repositories.health_repository import HealthRepository


class RoutingExhaustedError(RuntimeError):
    def __init__(
        self,
        attempts: list[InvocationAttempt],
        reason: str,
        *,
        request_id: UUID | None = None,
        scored_candidates: tuple[ScoredCandidate, ...] = (),
    ) -> None:
        super().__init__("All routing candidates failed")
        self.attempts = attempts
        self.reason = reason
        self.request_id = request_id
        self.scored_candidates = scored_candidates


class FallbackExecutor:
    def __init__(
        self,
        providers: dict[str, ProviderAdapter],
        *,
        max_total_attempts: int = 8,
        max_failures_per_model: int = 1,
        health_repository: HealthRepository | None = None,
        prefer_direct: bool = True,
    ) -> None:
        self.providers = providers
        self.max_total_attempts = max(1, int(max_total_attempts))
        self.max_failures_per_model = max(1, int(max_failures_per_model))
        self.health_repository = health_repository
        self.prefer_direct = prefer_direct

    def run(
        self,
        *,
        request: RoutedRequest,
        decision: RoutingDecision,
        on_attempt: Callable[[InvocationAttempt], None] | None = None,
    ) -> FallbackExecutionOutcome:
        attempts: list[InvocationAttempt] = []
        failures_by_model: dict[str, int] = {}

        for model in decision.candidates:
            if len(attempts) >= self.max_total_attempts:
                break
            if failures_by_model.get(model.model_id, 0) >= self.max_failures_per_model:
                continue

            # Selection logic based on prefer_direct
            provider_key = model.provider
            if self.prefer_direct:
                if provider_key not in self.providers:
                    provider_key = "openrouter"
            else:
                provider_key = "openrouter"

            provider = self.providers.get(provider_key) or self.providers["openrouter"]

            t0 = time.perf_counter()
            try:
                response = provider.generate(request, model)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                latency = response.latency_ms if response.latency_ms is not None else elapsed_ms
                attempt = InvocationAttempt(
                    provider=provider_key,
                    model_id=model.model_id,
                    status="success",
                    detail="Request completed",
                    latency_ms=latency,
                )
                attempts.append(attempt)
                if on_attempt is not None:
                    on_attempt(attempt)

                if self.health_repository is not None:
                    db_id = _db_id_for_model(model.model_id, decision.scored_candidates)
                    if db_id is not None:
                        self.health_repository.record_success(model_id=db_id)

                merged = replace(response, latency_ms=latency)
                return FallbackExecutionOutcome(response=merged, attempts=attempts)
            except ProviderError as exc:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                failures_by_model[model.model_id] = failures_by_model.get(model.model_id, 0) + 1
                attempt = InvocationAttempt(
                    provider=provider_key,
                    model_id=model.model_id,
                    status="failed",
                    detail=str(exc),
                    latency_ms=elapsed_ms,
                )
                attempts.append(attempt)
                if on_attempt is not None:
                    on_attempt(attempt)

                if self.health_repository is not None:
                    db_id = _db_id_for_model(model.model_id, decision.scored_candidates)
                    if db_id is not None:
                        self.health_repository.record_failure(model_id=db_id, reason=str(exc))

        raise RoutingExhaustedError(
            attempts=attempts,
            reason=decision.reason,
        )


def _db_id_for_model(model_id: str, scored: tuple[ScoredCandidate, ...]) -> int | None:
    for sc in scored:
        if sc.model.model_id == model_id:
            return sc.db_model_id
    return None
