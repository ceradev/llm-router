
import pytest
from packages.domain.gateway import Priority
from packages.domain.models import ModelProfile, Capability
from packages.core.scoring.engine import compute_model_score

def _model(**overrides: object) -> ModelProfile:
    payload: dict[str, object] = {
        "model_id": "test-model",
        "provider": "openai",
        "quality_score": 4,
        "latency_score": 4,
        "cost_score": 3,
        "default_temperature": 0.7,
        "capabilities": {Capability.CODE},
        "supports_tools": True,
        "context_window": 8192,
        "prompt_price": 0.000002,
        "completion_price": 0.000006,
    }
    payload.update(overrides)
    return ModelProfile(**payload)  # type: ignore[arg-type]


def test_exploration_bonus_is_bounded() -> None:
    model = _model()
    no_explore = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        complexity_score=0.1,
        prompt_tokens=200,
        exploration_enabled=False,
    )
    with_explore = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        complexity_score=0.1,
        prompt_tokens=200,
        exploration_enabled=True,
        total_attempts=100,
        model_attempts=0,
    )
    assert with_explore.exploration_bonus <= 0.10
    assert with_explore.total >= no_explore.total


def test_exploration_is_disabled_for_high_complexity_or_reasoning() -> None:
    model = _model()
    high_complexity = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        complexity_score=0.9,
        prompt_tokens=200,
        exploration_enabled=True,
        total_attempts=100,
        model_attempts=0,
    )
    reasoning_required = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        complexity_score=0.1,
        requires_reasoning=True,
        prompt_tokens=200,
        exploration_enabled=True,
        total_attempts=100,
        model_attempts=0,
    )
    assert high_complexity.exploration_bonus == pytest.approx(0.0)
    assert reasoning_required.exploration_bonus == pytest.approx(0.0)

if __name__ == "__main__":
    pytest.main([__file__])
