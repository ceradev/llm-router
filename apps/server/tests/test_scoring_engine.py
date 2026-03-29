from __future__ import annotations

from packages.core.scoring.engine import compute_model_score
from packages.domain.gateway import Priority
from packages.domain.models import Capability, ModelProfile


def test_compute_model_score_prefers_higher_total() -> None:
    low = ModelProfile(
        model_id="p/low",
        provider="p",
        quality_score=1,
        latency_score=1,
        cost_score=1,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )
    high = ModelProfile(
        model_id="p/high",
        provider="p",
        quality_score=5,
        latency_score=5,
        cost_score=5,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )

    low_score = compute_model_score(model=low, priority=Priority.BALANCED, priority_weight=100).total
    high_score = compute_model_score(model=high, priority=Priority.BALANCED, priority_weight=100).total

    assert high_score > low_score


def test_compute_model_score_includes_priority_weight() -> None:
    base = ModelProfile(
        model_id="p/m",
        provider="p",
        quality_score=3,
        latency_score=3,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
    )

    low = compute_model_score(model=base, priority=Priority.BALANCED, priority_weight=50).total
    high = compute_model_score(model=base, priority=Priority.BALANCED, priority_weight=150).total

    assert high > low


def _base_profile(**kwargs: object) -> ModelProfile:
    defaults: dict[str, object] = {
        "model_id": "openai/gpt-test",
        "provider": "openai",
        "quality_score": 3,
        "latency_score": 3,
        "cost_score": 3,
        "default_temperature": 0.2,
        "capabilities": {Capability.GENERAL},
        "supports_tools": False,
    }
    defaults.update(kwargs)
    return ModelProfile(**defaults)  # type: ignore[arg-type]


def test_use_case_api_boosts_json_model() -> None:
    without_json = _base_profile(capabilities={Capability.GENERAL})
    with_json = _base_profile(capabilities={Capability.GENERAL, Capability.JSON})

    base_kw = dict(priority=Priority.BALANCED, priority_weight=100)
    no_uc = compute_model_score(model=with_json, **base_kw).total
    with_uc = compute_model_score(
        model=with_json,
        **base_kw,
        use_cases=["api"],
    ).total
    no_uc_plain = compute_model_score(model=without_json, **base_kw, use_cases=["api"]).total

    assert with_uc > no_uc
    assert with_uc > no_uc_plain


def test_preferred_provider_bonus() -> None:
    anthropic_model = _base_profile(model_id="anthropic/claude", provider="anthropic")
    openai_model = _base_profile(model_id="openai/gpt", provider="openai")

    kw = dict(priority=Priority.BALANCED, priority_weight=100)
    pref_anth = compute_model_score(
        model=anthropic_model,
        **kw,
        preferred_providers=["anthropic"],
    ).total
    pref_anth_openai = compute_model_score(
        model=openai_model,
        **kw,
        preferred_providers=["anthropic"],
    ).total
    assert pref_anth > pref_anth_openai
    assert compute_model_score(model=openai_model, **kw).total == pref_anth_openai


def test_chatbot_use_case_adjusts_latency_weighting() -> None:
    slower = _base_profile(model_id="m/slow", latency_score=2)
    faster = _base_profile(model_id="m/fast", latency_score=5)

    kw = dict(priority=Priority.BALANCED, priority_weight=100)
    with_chat = compute_model_score(model=faster, **kw, use_cases=["chatbot"])
    without = compute_model_score(model=faster, **kw)
    assert with_chat.latency_component != without.latency_component
    assert (
        compute_model_score(model=faster, **kw, use_cases=["chatbot"]).total
        > compute_model_score(model=slower, **kw, use_cases=["chatbot"]).total
    )

