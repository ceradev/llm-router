from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_model import LLMModel
    from packages.infrastructure.db.models.provider_sync_run import ProviderSyncRun


class Provider(TimestampMixin, Base, table=True):
    __tablename__ = "providers"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True, max_length=64)
    display_name: str = Field(max_length=128)
    api_base_url: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)

    models: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMModel",
            back_populates="provider",
            cascade="all, delete-orphan",
        ),
    )
    sync_runs: Any = Relationship(
        sa_relationship=sa_relationship(
            "ProviderSyncRun",
            back_populates="provider",
            cascade="all, delete-orphan",
        ),
    )

