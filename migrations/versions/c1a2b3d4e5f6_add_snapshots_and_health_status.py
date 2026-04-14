"""Add model_performance_snapshots and model_health_status tables.

Revision ID: c1a2b3d4e5f6
Revises: f9a8b7c6d5e4
Create Date: 2026-04-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f9a8b7c6d5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- model_performance_snapshots ---
    op.create_table(
        "model_performance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("p50_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_cost_per_1k_tokens", sa.Float(), nullable=True),
        sa.Column("success_rate_7d", sa.Float(), nullable=True),     # 0.0–1.0
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_model_perf_snapshots_model_recorded",
        "model_performance_snapshots",
        ["model_id", "recorded_at"],
        unique=False,
    )

    # --- model_health_status ---
    op.create_table(
        "model_health_status",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "model_id",
            sa.Integer(),
            sa.ForeignKey("llm_models.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,   # one active health row per model
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="healthy",
        ),  # healthy | degraded | broken
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("model_health_status")
    op.drop_index("ix_model_perf_snapshots_model_recorded", table_name="model_performance_snapshots")
    op.drop_table("model_performance_snapshots")
