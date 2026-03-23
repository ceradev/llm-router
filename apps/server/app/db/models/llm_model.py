from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model_capability import LLMModelCapability
    from app.db.models.llm_model_routing_settings import LLMModelRoutingSettings
    from app.db.models.provider import Provider


class LLMModel(TimestampMixin, Base):
    __tablename__ = "llm_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_model_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    external_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_json: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    provider: Mapped["Provider"] = relationship(back_populates="models")
    capabilities: Mapped[list["LLMModelCapability"]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )
    routing_settings: Mapped["LLMModelRoutingSettings | None"] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        uselist=False,
    )
