from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes.sync import get_sync_api_key, router as sync_router
from packages.infrastructure.db.session import request_session_has_pending_writes

SYNC_HEADERS = {"X-Sync-Key": "test-sync-key"}


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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
    app.include_router(sync_router)
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_sync_api_key] = lambda: "test-sync-key"

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_sync_models_requires_key(sync_client: TestClient) -> None:
    response = sync_client.post("/v1/sync/models")

    assert response.status_code == 401
    assert response.json() == {"detail": "X-Sync-Key required"}


def test_sync_models_rejects_invalid_key(sync_client: TestClient) -> None:
    response = sync_client.post("/v1/sync/models", headers={"X-Sync-Key": "wrong-key"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid sync key"}


def test_sync_models_returns_503_when_key_is_not_configured(sync_client: TestClient) -> None:
    app = cast(FastAPI, sync_client.app)
    app.dependency_overrides[get_sync_api_key] = lambda: None

    response = sync_client.post("/v1/sync/models", headers=SYNC_HEADERS)

    assert response.status_code == 503
    assert response.json() == {"detail": "Sync API key is not configured"}


def test_sync_models_allows_valid_key(
    sync_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_sync_models(self: object) -> SimpleNamespace:
        return SimpleNamespace(models_processed=3, models_created=1, models_updated=2)

    monkeypatch.setattr(
        "app.api.routes.sync.OpenRouterSyncService.sync_models",
        _fake_sync_models,
    )

    response = sync_client.post("/v1/sync/models", headers=SYNC_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "models_processed": 3,
        "models_created": 1,
        "models_updated": 2,
    }
