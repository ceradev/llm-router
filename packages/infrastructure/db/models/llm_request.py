from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_attempt import LLMAttempt
    from packages.infrastructure.db.models.llm_execution import LLMExecution
    from packages.infrastructure.db.models.llm_feedback import LLMFeedback
    from packages.infrastructure.db.models.llm_model import LLMModel
    from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
    from packages.infrastructure.db.models.request_analysis import RequestAnalysis


class LLMRequest(Base, table=True):
    __tablename__ = "llm_requests"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    prompt: str = Field(sa_column=Column(Text, nullable=False))
    intent: str = Field(max_length=64)
    priority: str = Field(max_length=64)
    require_json: bool = Field(default=False)
    selected_model_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("llm_models.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    fallback_used: bool = Field(default=False)
    session_id: str | None = Field(
        default=None,
        sa_column=Column(String(128), nullable=True, index=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    selected_model: Any = Relationship(
        sa_relationship=sa_relationship("LLMModel", back_populates="requests_selected"),
    )
    analysis: Any = Relationship(
        sa_relationship=sa_relationship(
            "RequestAnalysis",
            back_populates="request",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )
    evaluations: Any = Relationship(
        sa_relationship=sa_relationship(
            "ModelEvaluation",
            back_populates="request",
            cascade="all, delete-orphan",
        ),
    )
    executions: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMExecution",
            back_populates="request",
            cascade="all, delete-orphan",
        ),
    )
    attempts: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMAttempt",
            back_populates="request",
            cascade="all, delete-orphan",
        ),
    )
    feedback_entries: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMFeedback",
            back_populates="request",
            cascade="all, delete-orphan",
        ),
    )
