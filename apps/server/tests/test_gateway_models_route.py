from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.gateway import router as gateway_router
from packages.infrastructure.db.session import request_session_has_pending_writes
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import ModelBenchmarkRun
from packages.infrastructure.db.models.provider import Provider


@pytest.fixture
def gateway_client_and_engine() -> Generator[tuple[TestClient, Engine], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Provider.__table__.create(engine, checkfirst=True)
    LLMModel.__table__.create(engine, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(engine, checkfirst=True)
    LLMModelCapability.__table__.create(engine, checkfirst=True)
    ModelBenchmarkRun.__table__.create(engine, checkfirst=True)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            try:
                yield session
            except Exception:
                if session.in_transaction():
                    session.rollback()
                raise
            else:
                if request_session_has_pending_writes(session):
                    session.commit()
                elif session.in_transaction():
                    session.rollback()

    app = FastAPI()
    app.include_router(gateway_router)
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def _seed_db_model(engine: Engine) -> None:
    with Session(engine) as session:
        provider = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(provider)
        session.flush()

        assert provider.id is not None
        model = LLMModel(
            provider_id=provider.id,
            external_model_id="gpt-4.1-mini",
            routing_key="openai/gpt-4.1-mini",
            display_name="GPT 4.1 Mini",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            evaluation_status=ModelEvaluationStatus.VERIFIED,
        )
        session.add(model)
        session.flush()

        assert model.id is not None
        session.add(
            LLMModelRoutingSettings(
                model_id=model.id,
                quality_score=9,
                latency_score=7,
                cost_score=6,
                default_temperature=0.2,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()


def test_models_route_returns_fallback_models_when_db_catalog_is_empty(
    gateway_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, _engine = gateway_client_and_engine

    response = client.get("/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert body
    fallback_models = {item["model_id"]: item for item in body}
    assert {item["model_id"] for item in body} >= {
        "openai/gateway-fast",
        "anthropic/gateway-quality",
        "groq/gateway-low-latency",
        "deepseek/gateway-code",
    }
    assert fallback_models["openai/gateway-fast"]["provider"] == "openai"
    assert fallback_models["openai/gateway-fast"]["supports_json"] is True


def test_models_route_prefers_db_catalog_when_models_exist(
    gateway_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = gateway_client_and_engine
    _seed_db_model(engine)

    response = client.get("/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert [item["model_id"] for item in body] == ["openai/gpt-4.1-mini"]
    assert body[0]["provider"] == "openai"
    assert body[0]["supports_json"] is True
