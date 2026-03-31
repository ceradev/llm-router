from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.providers import router as providers_router
from packages.infrastructure.db.models.provider import Provider


@pytest.fixture
def providers_client_and_engine() -> Generator[tuple[TestClient, Engine], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(engine, checkfirst=True)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.include_router(providers_router)
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def test_list_providers_returns_200_and_list(
    providers_client_and_engine: tuple[TestClient, Engine],
) -> None:
    client, _engine = providers_client_and_engine
    response = client.get("/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body == []

    with Session(_engine) as session:
        session.add(
            Provider(slug="demo", display_name="Demo", is_active=True),
        )
        session.add(
            Provider(slug="off", display_name="Off", is_active=False),
        )
        session.commit()

    response2 = client.get("/v1/providers")
    assert response2.status_code == 200
    data = response2.json()
    assert len(data) == 1
    assert data[0]["slug"] == "demo"
    assert data[0]["display_name"] == "Demo"
    assert data[0]["is_active"] is True
    assert "id" in data[0]
