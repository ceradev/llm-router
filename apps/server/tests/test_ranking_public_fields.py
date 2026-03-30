from __future__ import annotations

from packages.domain.models import Capability, ModelProfile
from packages.schemas.ranking_public_fields import compute_model_type_labels, public_status_fields


def _base(**kwargs: object) -> ModelProfile:
    defaults: dict[str, object] = {
        "model_id": "openrouter/x/y",
        "provider": "x",
        "quality_score": 3,
        "latency_score": 3,
        "cost_score": 3,
        "default_temperature": 0.2,
        "capabilities": {Capability.GENERAL},
    }
    defaults.update(kwargs)
    return ModelProfile(**defaults)  # type: ignore[arg-type]


def test_public_status_fields_verified() -> None:
    v, k = public_status_fields("verified")
    assert v is True
    assert k == "verified"


def test_public_status_fields_provisional() -> None:
    v, k = public_status_fields("provisional")
    assert v is False
    assert k == "provisional"


def test_public_status_fields_cataloged_maps_to_available() -> None:
    v, k = public_status_fields("cataloged")
    assert v is False
    assert k == "available"


def test_public_status_fields_rejected() -> None:
    v, k = public_status_fields("rejected")
    assert v is False
    assert k is None


def test_compute_model_type_labels_chat_and_json() -> None:
    m = _base(capabilities={Capability.GENERAL, Capability.JSON})
    assert compute_model_type_labels(m) == ["chat", "json"]


def test_compute_model_type_labels_vision_implies_multimodal() -> None:
    m = _base(supports_vision=True, capabilities={Capability.GENERAL})
    assert compute_model_type_labels(m) == ["multimodal", "vision"]


def test_compute_model_type_labels_code_and_analysis() -> None:
    m = _base(capabilities={Capability.GENERAL, Capability.CODE, Capability.ANALYSIS})
    assert compute_model_type_labels(m) == ["chat", "code", "analysis"]


def test_compute_model_type_labels_tools() -> None:
    m = _base(supports_tools=True, capabilities={Capability.GENERAL})
    assert compute_model_type_labels(m) == ["chat", "tools"]
