from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlmodel import Field

from packages.infrastructure.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass

class ModelPerformanceSnapshot(Base, table=True):
    __tablename__ = "model_performance_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        sa_column=Column(Integer(), ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    p50_latency_ms: float | None = Field(default=None)
    p95_latency_ms: float | None = Field(default=None)
    avg_cost_per_1k_tokens: float | None = Field(default=None)
    success_rate_7d: float | None = Field(default=None)
    sample_size: int = Field(default=0)
    snapshot_version: str = Field(default="v1", max_length=32)
    recorded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
