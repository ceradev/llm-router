from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.requests import router as requests_router
from packages.infrastructure.db.models.llm_attempt import LLMAttempt
from packages.infrastructure.db.models.llm_execution import LLMExecution
from packages.infrastructure.db.models.llm_feedback import LLMFeedback
from packages.infrastructure.db.models.llm_model import LLMModel
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.models.provider import Provider


@pytest.fixture
def requests_client_and_engine() -> Generator[tuple[TestClient, Engine], None, None]:
    """SQLite in-memory: core FK chain + executions/attempts. ARRAY-backed tables are omitted; the
    repository loads analysis/evaluations/feedback separately and tolerates missing tables."""
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

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.include_router(requests_router)
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def _seed_provider_and_model(session: Session) -> tuple[int, int]:
    p = Provider(slug="test-prov", display_name="Test", is_active=True)
    session.add(p)
    session.flush()
    m = LLMModel(
        provider_id=p.id,
        external_model_id="ext-1",
        routing_key="openai/gpt-test",
        display_name="GPT Test",
        is_active=True,
        is_available=True,
        supports_json=False,
        supports_tools=False,
        supports_vision=False,
    )
    session.add(m)
    session.flush()
    assert p.id is not None and m.id is not None
    return p.id, m.id


def test_list_requests_no_session_returns_empty(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, _ = requests_client_and_engine
    r = client.get("/v1/requests")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_list_requests_filters_by_session(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = requests_client_and_engine
    sid_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    sid_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    with Session(engine) as session:
        _, mid = _seed_provider_and_model(session)
        r1 = LLMRequest(
            prompt="hello world",
            intent="general",
            priority="normal",
            require_json=False,
            session_id=sid_a,
            selected_model_id=mid,
            fallback_used=False,
        )
        r2 = LLMRequest(
            prompt="other",
            intent="general",
            priority="normal",
            require_json=False,
            session_id=sid_b,
            selected_model_id=mid,
            fallback_used=True,
        )
        session.add(r1)
        session.add(r2)
        session.commit()

    res = client.get("/v1/requests", headers={"X-Session-Id": sid_a})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["prompt"] == "hello world"
    assert data["items"][0]["selected_model"] == "openai/gpt-test"
    assert data["items"][0]["fallback_used"] is False


def test_get_request_detail_200(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = requests_client_and_engine
    with Session(engine) as session:
        _, mid = _seed_provider_and_model(session)
        req = LLMRequest(
            prompt="full prompt text",
            intent="code",
            priority="high",
            require_json=True,
            session_id="sess-1",
            selected_model_id=mid,
            fallback_used=False,
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        rid = str(req.id)

    r = client.get(
        f"/v1/requests/{rid}",
        headers={"X-Session-Id": "sess-1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["prompt"] == "full prompt text"
    assert body["intent"] == "code"
    assert body["priority"] == "high"
    assert body["require_json"] is True
    assert body["selected_model"] == "openai/gpt-test"
    assert body["analysis"] is None
    assert body["evaluations"] == []
    assert body["attempts"] == []
    assert body["feedback"] is None


def test_get_request_detail_wrong_session_403(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = requests_client_and_engine
    with Session(engine) as session:
        _, mid = _seed_provider_and_model(session)
        req = LLMRequest(
            prompt="x",
            intent="general",
            priority="normal",
            require_json=False,
            session_id="correct-session",
            selected_model_id=mid,
            fallback_used=False,
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        rid = str(req.id)

    r = client.get(
        f"/v1/requests/{rid}",
        headers={"X-Session-Id": "wrong-session"},
    )
    assert r.status_code == 403


def test_post_feedback_201(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = requests_client_and_engine
    with Session(engine) as session:
        _, mid = _seed_provider_and_model(session)
        req = LLMRequest(
            prompt="x",
            intent="general",
            priority="normal",
            require_json=False,
            session_id="feedback-session",
            selected_model_id=mid,
            fallback_used=False,
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        rid = str(req.id)

    r = client.post(
        f"/v1/requests/{rid}/feedback",
        json={"rating": 5, "comment": "great"},
        headers={"X-Session-Id": "feedback-session"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["rating"] == 5
    assert body["comment"] == "great"
    assert body["request_id"] == rid
    assert body["model_id"] == mid


def test_post_feedback_400_without_selected_model(
    requests_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, engine = requests_client_and_engine

    with Session(engine) as session:
        _, _mid = _seed_provider_and_model(session)
        req = LLMRequest(
            prompt="x",
            intent="general",
            priority="normal",
            require_json=False,
            session_id="feedback-session-2",
            selected_model_id=None,
            fallback_used=False,
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        rid = str(req.id)

    r = client.post(
        f"/v1/requests/{rid}/feedback",
        json={"rating": 4},
        headers={"X-Session-Id": "feedback-session-2"},
    )
    assert r.status_code == 400
