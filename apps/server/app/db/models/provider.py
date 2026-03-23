from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model import LLMModel
    from app.db.models.provider_sync_run import ProviderSyncRun


class Provider(TimestampMixin, Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    models: Mapped[list["LLMModel"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    sync_runs: Mapped[list["ProviderSyncRun"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
    )
