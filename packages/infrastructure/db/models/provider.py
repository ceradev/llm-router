from __future__ import annotations

from typing import TYPE_CHECKING

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

    models: list["LLMModel"] = Relationship(
        back_populates="provider",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    sync_runs: list["ProviderSyncRun"] = Relationship(
        back_populates="provider",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

