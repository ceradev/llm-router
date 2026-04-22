from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine
from sqlmodel import select

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.admin import get_admin_api_key, router as admin_router
from packages.infrastructure.db.session import request_session_has_pending_writes
from packages.infrastructure.db.models.daily_metrics import DailyMetrics
from packages.infrastructure.db.models.llm_attempt import LLMAttempt
from packages.infrastructure.db.models.llm_execution import LLMExecution
from packages.infrastructure.db.models.llm_feedback import LLMFeedback
from packages.infrastructure.db.models.llm_model import LLMModel
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import ModelBenchmarkRun
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.models.provider import Provider

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture
def admin_client_and_engine() -> Generator[tuple[TestClient, Engine], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Provider.__table__.create(engine, checkfirst=True)
    LLMModel.__table__.create(engine, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(engine, checkfirst=True)
    LLMRequest.__table__.create(engine, checkfirst=True)
    LLMExecution.__table__.create(engine, checkfirst=True)
    LLMAttempt.__table__.create(engine, checkfirst=True)
    LLMFeedback.__table__.create(engine, checkfirst=True)
    ModelBenchmarkRun.__table__.create(engine, checkfirst=True)
    DailyMetrics.__table__.create(engine, checkfirst=True)

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
    app.include_router(admin_router)
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_admin_api_key] = lambda: "test-admin-key"

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def _seed_provider_model_request_data(session: Session) -> tuple[int, str]:
    provider = Provider(slug="openrouter", display_name="OpenRouter", is_active=True)
    session.add(provider)
    session.flush()

    assert provider.id is not None
    model = LLMModel(
        provider_id=provider.id,
        external_model_id="gpt-test",
        routing_key="openrouter/openai/gpt-test",
        display_name="GPT Test",
        is_active=True,
        is_available=True,
        supports_json=True,
        supports_tools=False,
        supports_vision=False,
        tier="premium",
    )
    session.add(model)
    session.flush()
    assert model.id is not None

    req_ok = LLMRequest(
        prompt="success request",
        intent="general",
        priority="normal",
        require_json=False,
        selected_model_id=model.id,
        fallback_used=False,
        created_at=datetime.combine(date.today(), datetime.min.time()),
    )
    req_fb = LLMRequest(
        prompt="fallback request",
        intent="general",
        priority="normal",
        require_json=False,
        selected_model_id=model.id,
        fallback_used=True,
        created_at=datetime.combine(date.today(), datetime.min.time()),
    )
    session.add(req_ok)
    session.add(req_fb)
    session.flush()

    session.add(
        LLMExecution(
            request_id=req_ok.id,
            model_id=model.id,
            input_tokens=10,
            output_tokens=20,
            latency_ms=100,
            cost=0.1,
            success=True,
        )
    )
    session.add(
        LLMExecution(
            request_id=req_fb.id,
            model_id=model.id,
            input_tokens=10,
            output_tokens=20,
            latency_ms=120,
            cost=0.2,
            success=True,
        )
    )
    session.add(LLMFeedback(model_id=model.id, request_id=req_ok.id, rating=4, comment="good"))
    session.add(LLMFeedback(model_id=model.id, request_id=req_fb.id, rating=5, comment="great"))
    session.add(
        DailyMetrics(
            metric_date=date.today(),
            total_requests=2,
            successful_requests=2,
            failed_requests=0,
            avg_latency_ms=110.0,
            unique_sessions=1,
        )
    )
    session.commit()
    return model.id, model.routing_key


def test_admin_requires_key(admin_client_and_engine: tuple[TestClient, Engine]) -> None:
    client, _engine = admin_client_and_engine
    response = client.get("/v1/admin/dashboard")
    assert response.status_code == 401


def test_dashboard_returns_counts(admin_client_and_engine: tuple[TestClient, Engine]) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _seed_provider_model_request_data(session)
    response = client.get("/v1/admin/dashboard", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["total_models"] == 1
    assert body["total_providers"] == 1
    assert body["requests_today"] == 2


def test_models_and_model_detail(admin_client_and_engine: tuple[TestClient, Engine]) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _model_id, routing_key = _seed_provider_model_request_data(session)

    list_response = client.get("/v1/admin/models?provider=openrouter&tier=premium", headers=ADMIN_HEADERS)
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["routing_key"] == routing_key

    detail_response = client.get(f"/v1/admin/models/{routing_key}", headers=ADMIN_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["selected_count"] == 2
    assert detail["average_rating"] == pytest.approx(4.5)
    assert detail["rating_count"] == 2


def test_admin_requests_and_metrics(admin_client_and_engine: tuple[TestClient, Engine]) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _seed_provider_model_request_data(session)

    requests_response = client.get(
        f"/v1/admin/requests?date={date.today().isoformat()}&limit=20",
        headers=ADMIN_HEADERS,
    )
    assert requests_response.status_code == 200
    items = requests_response.json()["items"]
    assert len(items) == 2
    statuses = {item["status"] for item in items}
    assert "success" in statuses
    assert "fallback" in statuses

    metrics_response = client.get("/v1/admin/metrics?days=7", headers=ADMIN_HEADERS)
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["total_requests"] == 2
    assert metrics["successful_requests"] == 2


def test_admin_sync_run(admin_client_and_engine: tuple[TestClient, Engine], monkeypatch: pytest.MonkeyPatch) -> None:
    client, _engine = admin_client_and_engine

    def _fake_sync_models(self: object) -> SimpleNamespace:
        return SimpleNamespace(models_processed=3, models_created=1, models_updated=2)

    monkeypatch.setattr(
        "app.api.routes.admin.OpenRouterSyncService.sync_models",
        _fake_sync_models,
    )
    response = client.post("/v1/admin/sync/run", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["models_processed"] == 3
    assert body["models_created"] == 1
    assert body["models_updated"] == 2


def test_admin_model_evaluate_returns_structured_payload(
    admin_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _model_id, routing_key = _seed_provider_model_request_data(session)

    response = client.post(
        f"/v1/admin/models/{routing_key}/evaluate?mode=heuristic&enable_image_text_v2=true&enable_file_text_v3=true",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["routing_key"] == routing_key
    assert body["mode"] == "heuristic"
    assert isinstance(body["benchmark_run_id"], int)
    assert body["benchmark_scope"] in {"text", "image_to_text"}
    assert isinstance(body["cases"], list)

    with Session(engine) as session:
        persisted_run = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.id == body["benchmark_run_id"])
        ).first()
        assert persisted_run is not None


def test_admin_model_batch_evaluate_with_filters(
    admin_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _seed_provider_model_request_data(session)

    response = client.post(
        "/v1/admin/models/evaluate-batch?mode=heuristic&provider=openrouter&evaluation_status=cataloged&limit=10&enable_file_text_v3=true",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "heuristic"
    assert body["matched_models"] == 1
    assert body["processed_models"] == 1
    assert body["succeeded"] + body["failed"] + body["skipped"] == 1
    assert isinstance(body["failed_reason_counts"], dict)
    assert isinstance(body["failed_models"], list)


def test_admin_model_batch_live_cataloged_counts_as_skipped_precondition(
    admin_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = admin_client_and_engine
    with Session(engine) as session:
        _seed_provider_model_request_data(session)

    response = client.post(
        "/v1/admin/models/evaluate-batch?mode=live&provider=openrouter&evaluation_status=cataloged&limit=10",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "live"
    assert body["matched_models"] == 1
    assert body["processed_models"] == 1
    assert body["succeeded"] == 0
    assert body["failed"] == 0
    assert body["skipped"] == 1
    assert body["benchmark_status_counts"].get("skipped_precondition") == 1
    assert body["skip_reason_counts"].get("requires_heuristic_first") == 1
    assert body["error_messages"] == []
