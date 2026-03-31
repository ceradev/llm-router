from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_request import LLMRequest


class RequestAnalysis(Base, table=True):
    __tablename__ = "request_analysis"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    request_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("llm_requests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
    )
    task_type: str = Field(max_length=64)
    complexity_score: float = Field(sa_column=Column(Float, nullable=False))
    cost_sensitivity: float = Field(sa_column=Column(Float, nullable=False))
    latency_sensitivity: float = Field(sa_column=Column(Float, nullable=False))
    detected_skills: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String()), nullable=True),
    )
    tokens_estimated: int = Field(sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    request: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="analysis"),
    )
