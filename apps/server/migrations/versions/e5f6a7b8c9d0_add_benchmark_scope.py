"""Add benchmark_scope to model_benchmark_runs.

Revision ID: e5f6a7b8c9d0
Revises: b2c3d4e5f6a7
Create Date: 2026-03-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.add_column(
        "model_benchmark_runs",
        sa.Column(
            "benchmark_scope",
            sa.String(length=32),
            nullable=False,
            server_default="text",
        ),
    )
    op.create_index(
        op.f("ix_model_benchmark_runs_benchmark_scope"),
        "model_benchmark_runs",
        ["benchmark_scope"],
        unique=False,
    )
    op.alter_column("model_benchmark_runs", "benchmark_scope", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_benchmark_runs_benchmark_scope"), table_name="model_benchmark_runs")
    op.drop_column("model_benchmark_runs", "benchmark_scope")
