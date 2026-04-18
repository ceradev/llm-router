from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, SQLModel, Session, create_engine, select

import app.api.dependencies.orchestrator as orchestrator_dependency


class SessionLifecycleRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    label: str


def _build_lifecycle_app() -> FastAPI:
    app = FastAPI()

    @app.post("/success")
    def create_success_record(
        session: Session = Depends(orchestrator_dependency.get_db_session),
    ) -> dict[str, int]:
        session.info["track_lifecycle"] = True
        row = SessionLifecycleRecord(label="success")
        session.add(row)
        session.flush()
        assert row.id is not None
        return {"id": row.id}

    @app.post("/fail")
    def create_then_fail(
        session: Session = Depends(orchestrator_dependency.get_db_session),
    ) -> None:
        session.info["track_lifecycle"] = True
        row = SessionLifecycleRecord(label="rolled-back")
        session.add(row)
        session.flush()
        raise HTTPException(status_code=500, detail="boom")

    @app.get("/read-only")
    def read_only(
        session: Session = Depends(orchestrator_dependency.get_db_session),
    ) -> dict[str, int]:
        session.info["track_lifecycle"] = True
        rows = list(session.exec(select(SessionLifecycleRecord)).all())
        return {"count": len(rows)}

    return app


@pytest.fixture
def lifecycle_client_and_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, Engine, dict[str, int]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    lifecycle_table = getattr(SessionLifecycleRecord, "__table__")
    SQLModel.metadata.create_all(engine, tables=[lifecycle_table])

    lifecycle_counts = {"commit": 0, "rollback": 0}
    original_commit = Session.commit
    original_rollback = Session.rollback

    def tracked_commit(self: Session) -> None:
        if self.bind is engine and self.info.get("track_lifecycle"):
            lifecycle_counts["commit"] += 1
        original_commit(self)

    def tracked_rollback(self: Session) -> None:
        if self.bind is engine and self.info.get("track_lifecycle"):
            lifecycle_counts["rollback"] += 1
        original_rollback(self)

    monkeypatch.setattr(orchestrator_dependency, "engine", engine)
    monkeypatch.setattr(Session, "commit", tracked_commit)
    monkeypatch.setattr(Session, "rollback", tracked_rollback)

    app = _build_lifecycle_app()
    with TestClient(app) as client:
        yield client, engine, lifecycle_counts


def test_success_path_commits_staged_writes(
    lifecycle_client_and_engine: tuple[TestClient, Engine, dict[str, int]],
) -> None:
    client, engine, lifecycle_counts = lifecycle_client_and_engine

    response = client.post("/success")

    assert response.status_code == 200
    assert lifecycle_counts == {"commit": 1, "rollback": 0}

    with Session(engine) as session:
        rows = list(session.exec(select(SessionLifecycleRecord)).all())
        assert len(rows) == 1
        assert rows[0].label == "success"


def test_exception_path_rolls_back_staged_writes(
    lifecycle_client_and_engine: tuple[TestClient, Engine, dict[str, int]],
) -> None:
    client, engine, lifecycle_counts = lifecycle_client_and_engine

    response = client.post("/fail")

    assert response.status_code == 500
    assert response.json() == {"detail": "boom"}
    assert lifecycle_counts == {"commit": 0, "rollback": 1}

    with Session(engine) as session:
        rows = list(session.exec(select(SessionLifecycleRecord)).all())
        assert rows == []


def test_read_only_path_avoids_commit_and_rolls_back_transaction(
    lifecycle_client_and_engine: tuple[TestClient, Engine, dict[str, int]],
) -> None:
    client, _engine, lifecycle_counts = lifecycle_client_and_engine

    response = client.get("/read-only")

    assert response.status_code == 200
    assert response.json() == {"count": 0}
    assert lifecycle_counts == {"commit": 0, "rollback": 1}
