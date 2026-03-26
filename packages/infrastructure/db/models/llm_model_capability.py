from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, UniqueConstraint
from sqlmodel import Field, Relationship

from packages.domain.models import Capability
from packages.infrastructure.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_model import LLMModel


class LLMModelCapability(TimestampMixin, Base, table=True):
    __tablename__ = "llm_model_capabilities"
    __table_args__ = (UniqueConstraint("model_id", "capability"),)

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        foreign_key="llm_models.id",
        index=True,
    )
    capability: Capability = Field(
        sa_column=Column(
            Enum(Capability, native_enum=False),
            nullable=False,
        )
    )

    model: "LLMModel" = Relationship(back_populates="capabilities")

