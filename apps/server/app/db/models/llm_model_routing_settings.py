from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model import LLMModel


class LLMModelRoutingSettings(TimestampMixin, Base):
    __tablename__ = "llm_model_routing_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("llm_models.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    allow_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled_for_routing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    model: Mapped["LLMModel"] = relationship(back_populates="routing_settings")
