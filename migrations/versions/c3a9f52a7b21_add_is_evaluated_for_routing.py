"""add is_evaluated_for_routing to routing settings

Revision ID: c3a9f52a7b21
Revises: f1a2b3c4d5e6
Create Date: 2026-03-30

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3a9f52a7b21"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_model_routing_settings",
        sa.Column("is_evaluated_for_routing", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Backfill policy:
    # - Curated seeded models (explicit scores) are considered evaluated and can be enabled.
    # - Everything else is cataloged but not evaluated, so it must not be enabled for routing.
    op.execute(
        sa.text(
            """
            UPDATE llm_model_routing_settings rs
            SET
              is_evaluated_for_routing = TRUE,
              enabled_for_routing = TRUE
            WHERE rs.model_id IN (
              SELECT m.id
              FROM llm_models m
              WHERE m.routing_key IN (
                'openrouter/openai/gpt-4o',
                'openrouter/anthropic/claude-3-haiku',
                'openrouter/deepseek/deepseek-coder',
                'openrouter/meta-llama/llama-3.1-70b-instruct',
                'openrouter/mistralai/mixtral-8x7b-instruct'
              )
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE llm_model_routing_settings
            SET enabled_for_routing = FALSE
            WHERE is_evaluated_for_routing = FALSE
            """
        )
    )

    # Remove server_default after backfill.
    op.alter_column("llm_model_routing_settings", "is_evaluated_for_routing", server_default=None)


def downgrade() -> None:
    op.drop_column("llm_model_routing_settings", "is_evaluated_for_routing")

