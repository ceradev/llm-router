
import pytest
from packages.domain.gateway import Priority, Intent
from packages.domain.models import ModelProfile, Capability
from packages.core.scoring.engine import compute_model_score

def test_intent_weights_code():
    model = ModelProfile(
        model_id="test-model",
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities={Capability.CODE},
        supports_tools=True
    )
    
    # Base score without intent
    base_score = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50
    )
    
    # Score with CODE intent
    code_score = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        intent=Intent.CODE
    )
    
    # CODE intent weights (1.15, 0.85, 0.70)
    # Balanced priority weights (0.6, 0.6, 0.6)
    
    # Base Balanced weights: 0.6 / 1.8 = 0.333
    # Quality weight = 80 * 0.333 = 26.66
    
    # Code weights applied to 0.6: (0.69, 0.51, 0.42)
    # Sum = 1.62
    # Renormalized: (0.426, 0.315, 0.259)
    # Quality component = 80 * 0.426 = 34.08
    
    assert code_score.quality_component > 26.66

def test_jitter_penalty():
    model = ModelProfile(
        model_id="test-model",
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities={Capability.CODE},
        supports_tools=True
    )
    
    # Base score without jitter
    base_score = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        jitter_penalty=0.0
    )
    
    # Score with jitter penalty
    jitter_val = 0.05
    jitter_score = compute_model_score(
        model=model,
        priority=Priority.BALANCED,
        priority_weight=50,
        jitter_penalty=jitter_val
    )
    
    # Check penalty was applied
    assert jitter_score.jitter_penalty == jitter_val
    assert jitter_score.base_total < base_score.base_total
    assert f"jitter={jitter_val:.2f}" in jitter_score.explanation

if __name__ == "__main__":
    pytest.main([__file__])
