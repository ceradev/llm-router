from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import Session, create_engine

from packages.infrastructure.config.settings import get_settings
import packages.infrastructure.db.models  # noqa: F401


settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)

_REQUEST_WRITE_FLAG = "request_write_pending"


@event.listens_for(SQLAlchemySession, "after_flush")
def _mark_request_write_pending(session: SQLAlchemySession, _flush_context: object) -> None:
    session.info[_REQUEST_WRITE_FLAG] = True


@event.listens_for(SQLAlchemySession, "after_commit")
@event.listens_for(SQLAlchemySession, "after_rollback")
def _clear_request_write_pending(session: SQLAlchemySession) -> None:
    session.info.pop(_REQUEST_WRITE_FLAG, None)


def request_session_has_pending_writes(session: Session) -> bool:
    return bool(
        session.info.get(_REQUEST_WRITE_FLAG)
        or session.new
        or session.dirty
        or session.deleted
    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

