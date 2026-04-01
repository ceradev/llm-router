"""Add OpenRouter catalog metadata to llm_models.

Revision ID: b7e1c2d3f4a5
Revises: c3a9f52a7b21
Create Date: 2026-03-30

This migration expands `llm_models` to store rich upstream metadata from OpenRouter
and a separate, explicit evaluation status for routing eligibility.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7e1c2d3f4a5"
down_revision: Union[str, Sequence[str], None] = "c3a9f52a7b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EVAL_STATUS_CATALOGED = "cataloged"
_EVAL_STATUS_VERIFIED = "verified"


def upgrade() -> None:
    op.add_column(
        "llm_models",
        sa.Column("openrouter_model_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("canonical_slug", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("hugging_face_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("upstream_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("modality", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("input_modalities", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("output_modalities", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("supported_parameters", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("default_parameters", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("per_request_limits", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("prompt_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("completion_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("input_cache_read_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("input_cache_write_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("is_moderated", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("knowledge_cutoff", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("expiration_date", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("upstream_metadata_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column(
            "evaluation_status",
            sa.String(length=32),
            nullable=False,
            server_default=_EVAL_STATUS_CATALOGED,
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column(
            "evaluation_confidence",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "llm_models",
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "llm_models",
        sa.Column("evaluation_version", sa.String(length=64), nullable=True),
    )

    op.create_index(op.f("ix_llm_models_openrouter_model_id"), "llm_models", ["openrouter_model_id"], unique=False)
    op.create_index(op.f("ix_llm_models_canonical_slug"), "llm_models", ["canonical_slug"], unique=False)
    op.create_index(op.f("ix_llm_models_evaluation_status"), "llm_models", ["evaluation_status"], unique=False)

    # Backfill for existing OpenRouter-synced rows.
    # routing_key is stored as "openrouter/{upstream_provider}/{model_suffix}" in this repo.
    op.execute(
        sa.text(
            """
            UPDATE llm_models
            SET
              openrouter_model_id = SUBSTRING(routing_key FROM 11),
              canonical_slug = SUBSTRING(routing_key FROM 11)
            WHERE routing_key LIKE 'openrouter/%'
              AND (openrouter_model_id IS NULL OR canonical_slug IS NULL)
            """
        )
    )

    # If a model is already marked evaluated-for-routing (curated/seeded), mark the catalog evaluation status verified.
    op.execute(
        sa.text(
            """
            UPDATE llm_models m
            SET
              evaluation_status = :verified,
              evaluation_confidence = 1,
              last_evaluated_at = now(),
              evaluation_version = 'seeded'
            WHERE EXISTS (
              SELECT 1
              FROM llm_model_routing_settings rs
              WHERE rs.model_id = m.id
                AND rs.is_evaluated_for_routing = TRUE
            )
            """
        ).bindparams(verified=_EVAL_STATUS_VERIFIED)
    )

    # Remove server defaults after backfill; application code provides defaults.
    op.alter_column("llm_models", "evaluation_status", server_default=None)
    op.alter_column("llm_models", "evaluation_confidence", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_models_evaluation_status"), table_name="llm_models")
    op.drop_index(op.f("ix_llm_models_canonical_slug"), table_name="llm_models")
    op.drop_index(op.f("ix_llm_models_openrouter_model_id"), table_name="llm_models")

    op.drop_column("llm_models", "evaluation_version")
    op.drop_column("llm_models", "last_evaluated_at")
    op.drop_column("llm_models", "evaluation_confidence")
    op.drop_column("llm_models", "evaluation_status")
    op.drop_column("llm_models", "upstream_metadata_json")
    op.drop_column("llm_models", "expiration_date")
    op.drop_column("llm_models", "knowledge_cutoff")
    op.drop_column("llm_models", "is_moderated")
    op.drop_column("llm_models", "input_cache_write_price")
    op.drop_column("llm_models", "input_cache_read_price")
    op.drop_column("llm_models", "completion_price")
    op.drop_column("llm_models", "prompt_price")
    op.drop_column("llm_models", "per_request_limits")
    op.drop_column("llm_models", "default_parameters")
    op.drop_column("llm_models", "supported_parameters")
    op.drop_column("llm_models", "output_modalities")
    op.drop_column("llm_models", "input_modalities")
    op.drop_column("llm_models", "modality")
    op.drop_column("llm_models", "upstream_created_at")
    op.drop_column("llm_models", "description")
    op.drop_column("llm_models", "hugging_face_id")
    op.drop_column("llm_models", "canonical_slug")
    op.drop_column("llm_models", "openrouter_model_id")
