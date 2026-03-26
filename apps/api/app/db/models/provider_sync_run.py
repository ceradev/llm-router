from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.provider import Provider


class ProviderSyncRun(TimestampMixin, Base, table=True):
    """Audit row for each synchronization attempt against a provider model API."""

    __tablename__ = "provider_sync_runs"

    id: int | None = Field(default=None, primary_key=True)
    provider_id: int = Field(
        foreign_key="providers.id",
        index=True,
    )
    status: str = Field(max_length=32)
    models_found: int = Field(default=0)
    models_updated: int = Field(default=0)
    error_message: str | None = Field(default=None)
    started_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        )
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    provider: "Provider" = Relationship(back_populates="sync_runs")
