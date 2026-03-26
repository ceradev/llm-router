from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model import LLMModel


class LLMModelRoutingSettings(TimestampMixin, Base, table=True):
    """Internal routing knobs kept separate from provider-discovered model metadata."""

    __tablename__ = "llm_model_routing_settings"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        foreign_key="llm_models.id",
        unique=True,
    )
    quality_score: int = Field(default=0)
    latency_score: int = Field(default=0)
    cost_score: int = Field(default=0)
    default_temperature: float = Field(default=0.2)
    priority_weight: int = Field(default=100)
    allow_fallback: bool = Field(default=True)
    enabled_for_routing: bool = Field(default=True)
    notes: str | None = Field(default=None)

    model: "LLMModel" = Relationship(back_populates="routing_settings")
