from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, Enum as SAEnum, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship

from packages.infrastructure.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from packages.infrastructure.db.models.llm_execution import LLMExecution
    from packages.infrastructure.db.models.llm_feedback import LLMFeedback
    from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
    from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
    from packages.infrastructure.db.models.llm_request import LLMRequest
    from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
    from packages.infrastructure.db.models.provider import Provider


class ModelEvaluationStatus(str, Enum):
    """Catalog-level evaluation state.

    This is intentionally distinct from operational routing flags in
    `llm_model_routing_settings`.

    - `provisional`: passed heuristic/metadata screening only; not execution-verified.
    - `verified`: passed live benchmark against the provider (see `model_benchmark_runs.benchmark_kind`).
    """

    CATALOGED = "cataloged"
    PROVISIONAL = "provisional"
    VERIFIED = "verified"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


_CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"


class LLMModel(TimestampMixin, Base, table=True):
    __tablename__ = "llm_models"
    __table_args__ = (UniqueConstraint("provider_id", "external_model_id"),)

    id: int | None = Field(default=None, primary_key=True)
    provider_id: int = Field(
        foreign_key="providers.id",
        index=True,
    )
    external_model_id: str = Field(max_length=255)
    routing_key: str = Field(unique=True, max_length=255)
    display_name: str = Field(max_length=255)
    # OpenRouter catalog metadata (declared upstream).
    openrouter_model_id: str | None = Field(default=None, max_length=255, index=True)
    canonical_slug: str | None = Field(default=None, max_length=255, index=True)
    hugging_face_id: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text(), nullable=True))
    upstream_created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    modality: str | None = Field(default=None, max_length=32)
    input_modalities: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    output_modalities: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    supported_parameters: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    default_parameters: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    per_request_limits: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    prompt_price: float | None = Field(default=None)
    completion_price: float | None = Field(default=None)
    input_cache_read_price: float | None = Field(default=None)
    input_cache_write_price: float | None = Field(default=None)
    is_moderated: bool | None = Field(default=None)
    knowledge_cutoff: str | None = Field(default=None, max_length=32)
    expiration_date: str | None = Field(default=None, max_length=32)
    upstream_metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    # Evaluation state (verified/curated); synced models are cataloged by default.
    evaluation_status: ModelEvaluationStatus = Field(
        default=ModelEvaluationStatus.CATALOGED,
        sa_column=Column(
            SAEnum(
                ModelEvaluationStatus,
                native_enum=False,
                values_callable=lambda enum_cls: [item.value for item in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    evaluation_confidence: float = Field(default=0.0)
    last_evaluated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    evaluation_version: str | None = Field(default=None, max_length=64)
    is_active: bool = Field(default=True)
    is_available: bool = Field(default=True)
    supports_json: bool = Field(default=False)
    supports_tools: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    tier: str = Field(default="alternative", max_length=32)
    context_window: int | None = Field(default=None)
    max_output_tokens: int | None = Field(default=None)
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    last_seen_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )

    provider: Any = Relationship(
        sa_relationship=sa_relationship("Provider", back_populates="models"),
    )
    capabilities: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMModelCapability",
            back_populates="model",
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )
    routing_settings: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMModelRoutingSettings",
            back_populates="model",
            uselist=False,
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )
    requests_selected: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="selected_model"),
    )
    evaluations: Any = Relationship(
        sa_relationship=sa_relationship(
            "ModelEvaluation",
            back_populates="model",
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )
    benchmark_runs: Any = Relationship(
        sa_relationship=sa_relationship(
            "ModelBenchmarkRun",
            back_populates="model",
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )
    executions: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMExecution",
            back_populates="model",
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )
    feedback_entries: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMFeedback",
            back_populates="model",
            cascade=_CASCADE_ALL_DELETE_ORPHAN,
        ),
    )

