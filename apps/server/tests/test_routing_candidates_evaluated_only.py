from __future__ import annotations

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from packages.domain.gateway import Priority
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.provider import Provider


def test_list_routing_candidates_excludes_not_evaluated_even_if_enabled() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(engine, checkfirst=True)
    LLMModel.__table__.create(engine, checkfirst=True)
    LLMModelCapability.__table__.create(engine, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(engine, checkfirst=True)

    with Session(engine) as session:
        p = Provider(slug="p", display_name="P", is_active=True)
        session.add(p)
        session.flush()
        assert p.id is not None

        m = LLMModel(
            provider_id=p.id,
            external_model_id="m1",
            routing_key="openrouter/p/m1",
            display_name="M1",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="alternative",
            context_window=None,
            max_output_tokens=None,
        )
        session.add(m)
        session.flush()
        assert m.id is not None

        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=3,
                latency_score=3,
                cost_score=3,
                enabled_for_routing=True,
                is_evaluated_for_routing=False,
            )
        )
        session.commit()

        repo = ModelRepository(session)
        out = repo.list_routing_candidates(priority=Priority.BALANCED, require_json=False)
        assert out == []


def test_list_routing_candidates_includes_evaluated_when_enabled() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(engine, checkfirst=True)
    LLMModel.__table__.create(engine, checkfirst=True)
    LLMModelCapability.__table__.create(engine, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(engine, checkfirst=True)

    with Session(engine) as session:
        p = Provider(slug="p", display_name="P", is_active=True)
        session.add(p)
        session.flush()
        assert p.id is not None

        m = LLMModel(
            provider_id=p.id,
            external_model_id="m2",
            routing_key="openrouter/p/m2",
            display_name="M2",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="alternative",
            context_window=None,
            max_output_tokens=None,
            evaluation_status=ModelEvaluationStatus.VERIFIED,
        )
        session.add(m)
        session.flush()
        assert m.id is not None

        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=5,
                latency_score=5,
                cost_score=5,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()

        repo = ModelRepository(session)
        out = repo.list_routing_candidates(priority=Priority.BALANCED, require_json=False)
        assert len(out) == 1
        assert out[0].model.model_id == "openrouter/p/m2"

