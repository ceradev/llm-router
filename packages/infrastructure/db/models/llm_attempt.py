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
    from packages.infrastructure.db.models.llm_request import LLMRequest


class LLMAttempt(Base, table=True):
    __tablename__ = "llm_attempts"

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
    provider_slug: str = Field(max_length=64)
    model_routing_key: str = Field(max_length=255)
    attempt_order: int = Field(sa_column=Column(Integer, nullable=False))
    status: str = Field(max_length=32)
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    latency_ms: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    request: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="attempts"),
    )
