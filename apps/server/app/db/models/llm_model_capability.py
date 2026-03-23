from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.types import Capability
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model import LLMModel


class LLMModelCapability(TimestampMixin, Base):
    __tablename__ = "llm_model_capabilities"
    __table_args__ = (
        UniqueConstraint("model_id", "capability"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("llm_models.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    capability: Mapped[Capability] = mapped_column(
        Enum(Capability, native_enum=False),
        nullable=False,
    )

    model: Mapped["LLMModel"] = relationship(back_populates="capabilities")
