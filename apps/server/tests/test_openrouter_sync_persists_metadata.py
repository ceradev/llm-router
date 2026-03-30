from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.provider import Provider
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService


def test_openrouter_sync_persists_rich_metadata_and_keeps_model_not_evaluated() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(engine, checkfirst=True)
    LLMModel.__table__.create(engine, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(engine, checkfirst=True)

    raw_model = {
        "id": "openai/gpt-4o-mini",
        "canonical_slug": "openai/gpt-4o-mini",
        "hugging_face_id": None,
        "name": "GPT-4o Mini",
        "created": 1710000000,
        "description": "Test model.",
        "pricing": {
            "prompt": "0.00000015",
            "completion": "0.00000060",
            "input_cache_read": "0.00000001",
            "input_cache_write": "0.00000002",
        },
        "context_length": 128000,
        "architecture": {
            "modality": "text",
            "input_modalities": ["text", "image"],
            "output_modalities": ["text"],
            "tokenizer": "GPT",
            "instruct_type": "none",
        },
        "top_provider": {"max_completion_tokens": 16384, "is_moderated": True, "context_length": 128000},
        "per_request_limits": {"prompt_tokens": 123, "completion_tokens": 456},
        "supported_parameters": ["tools", "structured_outputs", "temperature"],
        "default_parameters": {"temperature": 0.2, "top_p": 0.95},
        "knowledge_cutoff": "2024-06-01",
        "expiration_date": None,
    }

    with Session(engine) as session:
        svc = OpenRouterSyncService(session)
        svc._client.fetch_models = lambda: [raw_model]  # type: ignore[method-assign]
        out = svc.sync_models()
        assert out.models_processed == 1
        assert out.models_created == 1
        assert out.failures == []

        m = session.exec(select(LLMModel).where(LLMModel.routing_key == "openrouter/openai/gpt-4o-mini")).one()
        assert m.openrouter_model_id == "openai/gpt-4o-mini"
        assert m.canonical_slug == "openai/gpt-4o-mini"
        assert m.description == "Test model."
        assert m.modality == "text"
        assert m.input_modalities == ["text", "image"]
        assert m.output_modalities == ["text"]
        assert m.supported_parameters == ["tools", "structured_outputs", "temperature"]
        assert isinstance(m.default_parameters, dict)
        assert m.default_parameters.get("temperature") == pytest.approx(0.2)
        assert isinstance(m.per_request_limits, dict)
        assert m.per_request_limits.get("prompt_tokens") == 123
        assert m.prompt_price == pytest.approx(0.00000015)
        assert m.completion_price == pytest.approx(0.00000060)
        assert m.input_cache_read_price == pytest.approx(0.00000001)
        assert m.input_cache_write_price == pytest.approx(0.00000002)
        assert m.is_moderated is True
        assert m.knowledge_cutoff == "2024-06-01"
        assert m.expiration_date is None
        assert isinstance(m.upstream_metadata_json, dict)
        assert m.upstream_metadata_json.get("id") == "openai/gpt-4o-mini"

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == m.id)).one()
        assert rs.enabled_for_routing is False
        assert rs.is_evaluated_for_routing is False
        assert m.evaluation_status == ModelEvaluationStatus.CATALOGED

