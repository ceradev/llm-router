from __future__ import annotations

import pytest

from packages.domain.gateway import Intent, RoutedRequest, RoutingDecision
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.providers.base import ProviderError
from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.services.execution.fallback_executor import FallbackExecutor, RoutingExhaustedError


def _model(model_id: str, *, provider: str = "openrouter") -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider=provider,
        quality_score=3,
        latency_score=3,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )


def _decision(candidates: list[ModelProfile]) -> RoutingDecision:
    return RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.2,
        candidates=candidates,
        scored_candidates=(),
    )


class _CountingProvider(DemoProviderClient):
    def __init__(self, provider_name: str, *, fail_models: set[str] | None = None) -> None:
        super().__init__(provider_name)
        self.calls: list[str] = []
        self._fail_models = fail_models or set()

    def generate(self, request: RoutedRequest, model: ModelProfile):  # type: ignore[override]
        self.calls.append(model.model_id)
        if model.model_id in self._fail_models:
            raise ProviderError(f"forced failure {model.model_id}")
        return super().generate(request, model)


def test_executor_skips_repeated_failed_model_and_moves_to_next() -> None:
    provider = _CountingProvider("openrouter", fail_models={"openrouter/a"})
    executor = FallbackExecutor({"openrouter": provider}, max_failures_per_model=1)
    decision = _decision([_model("openrouter/a"), _model("openrouter/a"), _model("openrouter/b")])
    request = RoutedRequest(
        prompt="hello",
        temperature=0.2,
        max_tokens=64,
        require_json=False,
    )

    out = executor.run(request=request, decision=decision)

    assert out.response.model_id == "openrouter/b"
    assert provider.calls == ["openrouter/a", "openrouter/b"]
    assert [a.model_id for a in out.attempts] == ["openrouter/a", "openrouter/b"]


def test_executor_stops_after_max_total_attempts() -> None:
    provider = _CountingProvider(
        "openrouter",
        fail_models={"openrouter/a", "openrouter/b", "openrouter/c"},
    )
    executor = FallbackExecutor({"openrouter": provider}, max_total_attempts=2)
    decision = _decision([_model("openrouter/a"), _model("openrouter/b"), _model("openrouter/c")])
    request = RoutedRequest(
        prompt="hello",
        temperature=0.2,
        max_tokens=64,
        require_json=False,
    )

    with pytest.raises(RoutingExhaustedError) as exc:
        executor.run(request=request, decision=decision)

    assert len(exc.value.attempts) == 2
    assert provider.calls == ["openrouter/a", "openrouter/b"]
