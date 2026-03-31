from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_model import LLMModel


class BenchmarkRunStatus(str, Enum):
    """Lifecycle of a single catalog-level benchmark row."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"


class BenchmarkKind(str, Enum):
    """Distinguishes metadata-only screening from execution-backed verification."""

    HEURISTIC = "heuristic"
    LIVE = "live"


class BenchmarkScope(str, Enum):
    """Functional scope a benchmark run validates."""

    TEXT = "text"
    CODE = "code"
    JSON_TOOLS = "json_tools"
    VISION = "vision"
    OCR = "ocr"
    IMAGE_TO_TEXT = "image_to_text"
    FILE_TO_TEXT = "file_to_text"


class ModelBenchmarkRun(Base, table=True):
    """Persistent catalog-level benchmark history (not per-request `model_evaluations`)."""

    __tablename__ = "model_benchmark_runs"

    id: int | None = Field(default=None, primary_key=True)
    model_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("llm_models.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    evaluation_version: str = Field(max_length=64)
    # Values: `BenchmarkKind` (`heuristic` = metadata screening; `live` = provider execution).
    benchmark_kind: str = Field(default=BenchmarkKind.HEURISTIC.value, max_length=32, index=True)
    # Values: `BenchmarkScope`; `text` is current MVP verification scope.
    benchmark_scope: str = Field(default=BenchmarkScope.TEXT.value, max_length=32, index=True)
    # Values: `BenchmarkRunStatus` (stored as plain string for portability).
    status: str = Field(max_length=32, index=True)
    quality_score: int = Field(default=0)
    latency_score: int = Field(default=0)
    cost_score: int = Field(default=0)
    json_reliability: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    tool_reliability: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    error_rate: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    sample_size: int = Field(default=0)
    summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    raw_results_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    model: Any = Relationship(
        sa_relationship=sa_relationship("LLMModel", back_populates="benchmark_runs"),
    )
