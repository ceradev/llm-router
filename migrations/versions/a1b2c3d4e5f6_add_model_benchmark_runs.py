"""Add model_benchmark_runs for catalog-level benchmark history.

Revision ID: a1b2c3d4e5f6
Revises: b7e1c2d3f4a5
Create Date: 2026-03-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b7e1c2d3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_benchmark_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("latency_score", sa.Integer(), nullable=False),
        sa.Column("cost_score", sa.Integer(), nullable=False),
        sa.Column("json_reliability", sa.Float(), nullable=False),
        sa.Column("tool_reliability", sa.Float(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_results_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["llm_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_benchmark_runs_model_id"), "model_benchmark_runs", ["model_id"], unique=False)
    op.create_index(op.f("ix_model_benchmark_runs_status"), "model_benchmark_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_benchmark_runs_status"), table_name="model_benchmark_runs")
    op.drop_index(op.f("ix_model_benchmark_runs_model_id"), table_name="model_benchmark_runs")
    op.drop_table("model_benchmark_runs")
