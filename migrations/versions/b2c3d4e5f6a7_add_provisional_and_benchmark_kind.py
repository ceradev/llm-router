"""Add provisional evaluation status and benchmark_kind on benchmark runs.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVISIONAL = "provisional"


def upgrade() -> None:
    op.add_column(
        "model_benchmark_runs",
        sa.Column(
            "benchmark_kind",
            sa.String(length=32),
            nullable=False,
            server_default="heuristic",
        ),
    )
    op.create_index(
        op.f("ix_model_benchmark_runs_benchmark_kind"),
        "model_benchmark_runs",
        ["benchmark_kind"],
        unique=False,
    )
    op.alter_column("model_benchmark_runs", "benchmark_kind", server_default=None)

    # Prior `verified` rows were heuristic/seed — not execution-verified.
    op.execute(
        sa.text(
            """
            UPDATE llm_models
            SET evaluation_status = :provisional
            WHERE evaluation_status = 'verified'
            """
        ).bindparams(provisional=_PROVISIONAL)
    )

    op.execute(
        sa.text(
            """
            UPDATE llm_model_routing_settings
            SET
              enabled_for_routing = FALSE,
              is_evaluated_for_routing = FALSE
            WHERE model_id IN (
              SELECT id FROM llm_models WHERE evaluation_status = :provisional
            )
            """
        ).bindparams(provisional=_PROVISIONAL)
    )


def downgrade() -> None:
    # Cannot restore prior evaluation_status without losing information; only drop column.
    op.drop_index(op.f("ix_model_benchmark_runs_benchmark_kind"), table_name="model_benchmark_runs")
    op.drop_column("model_benchmark_runs", "benchmark_kind")
