import pytest
from unittest.mock import MagicMock
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.domain.gateway import (
    RoutedRequest,
    RoutingDecision,
    ProviderResponse,
    Intent,
    ScoredCandidate,
    ModelTier,
    HealthState,
)
from packages.domain.models import ModelProfile
from packages.infrastructure.providers.base import ProviderAdapter, ProviderError

@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=ProviderAdapter)
    return provider

@pytest.fixture
def mock_health_repo():
    repo = MagicMock()
    return repo

@pytest.fixture
def model_profile():
    return ModelProfile(
        model_id="test-model",
        provider="anthropic",
        quality_score=80,
        latency_score=70,
        cost_score=60,
        default_temperature=0.7,
        context_window=8192,
    )

@pytest.fixture
def scored_candidate(model_profile):
    return ScoredCandidate(
        model=model_profile,
        priority_weight=1,
        db_model_id=123,
        rank=1,
        quality_score=0.8,
        latency_score=0.9,
        cost_score=0.9,
        final_score=0.85,
        model_score_adjustment=0.0,
        explanation="Test",
        pros=(),
        cons=(),
    )

def test_fallback_executor_health_record_success(mock_provider, mock_health_repo, model_profile, scored_candidate):
    # Setup
    mock_provider.generate.return_value = ProviderResponse(
        content="Success",
        provider="anthropic",
        model_id="test-model",
        latency_ms=100
    )
    
    executor = FallbackExecutor(
        providers={"anthropic": mock_provider},
        health_repository=mock_health_repo
    )
    
    request = RoutedRequest(prompt="hi", temperature=0.7, max_tokens=100, require_json=False)
    decision = RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.7,
        candidates=[model_profile],
        scored_candidates=(scored_candidate,)
    )
    
    # Run
    executor.run(request=request, decision=decision)
    
    # Verify
    mock_health_repo.record_success.assert_called_once_with(model_id=123)

def test_fallback_executor_health_record_failure(mock_provider, mock_health_repo, model_profile, scored_candidate):
    # Setup
    mock_provider.generate.side_effect = ProviderError("Failed")
    
    executor = FallbackExecutor(
        providers={"anthropic": mock_provider, "openrouter": MagicMock()},
        health_repository=mock_health_repo
    )
    
    request = RoutedRequest(prompt="hi", temperature=0.7, max_tokens=100, require_json=False)
    decision = RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.7,
        candidates=[model_profile],
        scored_candidates=(scored_candidate,)
    )
    
    # Run (expecting it to exhaust since only one model and it fails)
    from packages.services.execution.fallback_executor import RoutingExhaustedError
    with pytest.raises(RoutingExhaustedError):
        executor.run(request=request, decision=decision)
    
    # Verify
    mock_health_repo.record_failure.assert_called_once_with(model_id=123, reason="Failed")

def test_fallback_executor_prefer_direct_true(mock_provider, model_profile, scored_candidate):
    # Setup
    mock_provider.generate.return_value = ProviderResponse(
        content="Success",
        provider="anthropic",
        model_id="test-model"
    )
    
    openrouter_mock = MagicMock(spec=ProviderAdapter)
    
    executor = FallbackExecutor(
        providers={"anthropic": mock_provider, "openrouter": openrouter_mock},
        prefer_direct=True
    )
    
    request = RoutedRequest(prompt="hi", temperature=0.7, max_tokens=100, require_json=False)
    decision = RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.7,
        candidates=[model_profile],
        scored_candidates=(scored_candidate,)
    )
    
    # Run
    executor.run(request=request, decision=decision)
    
    # Verify: should use anthropic provider
    mock_provider.generate.assert_called_once()
    openrouter_mock.generate.assert_not_called()

def test_fallback_executor_prefer_direct_false(mock_provider, model_profile, scored_candidate):
    # Setup
    openrouter_mock = MagicMock(spec=ProviderAdapter)
    openrouter_mock.generate.return_value = ProviderResponse(
        content="Success",
        provider="openrouter",
        model_id="test-model"
    )
    
    executor = FallbackExecutor(
        providers={"anthropic": mock_provider, "openrouter": openrouter_mock},
        prefer_direct=False
    )
    
    request = RoutedRequest(prompt="hi", temperature=0.7, max_tokens=100, require_json=False)
    decision = RoutingDecision(
        intent=Intent.GENERAL,
        reason="test",
        applied_temperature=0.7,
        candidates=[model_profile],
        scored_candidates=(scored_candidate,)
    )
    
    # Run
    executor.run(request=request, decision=decision)
    
    # Verify: should use openrouter provider even if anthropic is available
    openrouter_mock.generate.assert_called_once()
    mock_provider.generate.assert_not_called()
