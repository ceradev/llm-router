from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, UniqueConstraint, func
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
            cascade="all, delete-orphan",
        ),
    )
    routing_settings: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMModelRoutingSettings",
            back_populates="model",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )
    requests_selected: Any = Relationship(
        sa_relationship=sa_relationship("LLMRequest", back_populates="selected_model"),
    )
    evaluations: Any = Relationship(
        sa_relationship=sa_relationship(
            "ModelEvaluation",
            back_populates="model",
            cascade="all, delete-orphan",
        ),
    )
    executions: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMExecution",
            back_populates="model",
            cascade="all, delete-orphan",
        ),
    )
    feedback_entries: Any = Relationship(
        sa_relationship=sa_relationship(
            "LLMFeedback",
            back_populates="model",
            cascade="all, delete-orphan",
        ),
    )

