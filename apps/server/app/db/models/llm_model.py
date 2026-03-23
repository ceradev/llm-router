from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, Relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.llm_model_capability import LLMModelCapability
    from app.db.models.llm_model_routing_settings import LLMModelRoutingSettings
    from app.db.models.provider import Provider


class LLMModel(TimestampMixin, Base, table=True):
    """Discovered provider model plus runtime-facing metadata used by the gateway."""

    __tablename__ = "llm_models"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_model_id"),
    )

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

    provider: "Provider" = Relationship(back_populates="models")
    capabilities: list["LLMModelCapability"] = Relationship(
        back_populates="model",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    routing_settings: "LLMModelRoutingSettings | None" = Relationship(
        back_populates="model",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
        },
    )
