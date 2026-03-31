from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_model import LLMModel
    from packages.infrastructure.db.models.llm_request import LLMRequest


class ModelEvaluation(Base, table=True):
    __tablename__ = "model_evaluations"

    # NOTE: This table represents per-request evaluation snapshots (tied to `llm_requests.id`),
    # not catalog benchmark history. Use `model_benchmark_runs` (see `benchmark_kind`),
    # plus `llm_models.evaluation_status` (`provisional` vs `verified`) for routing eligibility.

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
    quality_score: float = Field(sa_column=Column(Float, nullable=False))
    latency_score: float = Field(sa_column=Column(Float, nullable=False))
    cost_score: float = Field(sa_column=Column(Float, nullable=False))
    final_score: float = Field(sa_column=Column(Float, nullable=False))
    evaluation_rank: int = Field(sa_column=Column("rank", Integer(), nullable=False))
    explanation: str = Field(sa_column=Column(Text, nullable=False))
    pros: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String()), nullable=True),
    )
    cons: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String()), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    request: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="evaluations"),
    )
    model: Any = Relationship(
        sa_relationship=sa_relationship("LLMModel", back_populates="evaluations"),
    )
