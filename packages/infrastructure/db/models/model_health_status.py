from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, Text, func
from sqlmodel import Field

from packages.infrastructure.db.base import Base

class ModelHealthStatus(Base, table=True):
    __tablename__ = "model_health_status"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        sa_column=Column(Integer(), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
    )
    status: str = Field(default="healthy", max_length=32)
    consecutive_failures: int = Field(default=0)
    last_failure_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_success_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    failure_reason: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
