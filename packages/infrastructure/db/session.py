from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from packages.infrastructure.config.settings import get_settings
import packages.infrastructure.db.models  # noqa: F401


settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

