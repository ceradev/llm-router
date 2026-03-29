from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_model import LLMModel
    from packages.infrastructure.db.models.llm_request import LLMRequest


class LLMFeedback(Base, table=True):
    __tablename__ = "llm_feedback"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    request_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("llm_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    model_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("llm_models.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    rating: int = Field(sa_column=Column(Integer, nullable=False))
    comment: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    request: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="feedback_entries"),
    )
    model: Any = Relationship(
        sa_relationship=sa_relationship("LLMModel", back_populates="feedback_entries"),
    )
