from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.settings import get_settings
import app.db.models  # noqa: F401


settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Create database tables based on SQLModel models."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Obtain a database session for use in API endpoints."""
    with Session(engine) as session:
        yield session
