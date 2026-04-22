"""Scale routing quality/latency/cost scores from legacy 1–5 to 1–10.

Existing rows with values in 1..5 are doubled (e.g. 3 → 6). Zeros (unset) and
values already >5 are left unchanged.

Revision ID: a9b8c7d6e5f4
Revises: a1b2c3d4e5f7, c1a2b3d4e5f6
Create Date: 2026-04-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = ("a1b2c3d4e5f7", "c1a2b3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE llm_model_routing_settings
            SET
              quality_score = CASE
                WHEN quality_score BETWEEN 1 AND 5 THEN quality_score * 2
                ELSE quality_score
              END,
              latency_score = CASE
                WHEN latency_score BETWEEN 1 AND 5 THEN latency_score * 2
                ELSE latency_score
              END,
              cost_score = CASE
                WHEN cost_score BETWEEN 1 AND 5 THEN cost_score * 2
                ELSE cost_score
              END
            """
        )
    )


def downgrade() -> None:
    # Lossy: only reverses values that are even and in 2..10 (typical post-migration).
    op.execute(
        sa.text(
            """
            UPDATE llm_model_routing_settings
            SET
              quality_score = CASE
                WHEN quality_score IN (2, 4, 6, 8, 10) THEN quality_score / 2
                ELSE quality_score
              END,
              latency_score = CASE
                WHEN latency_score IN (2, 4, 6, 8, 10) THEN latency_score / 2
                ELSE latency_score
              END,
              cost_score = CASE
                WHEN cost_score IN (2, 4, 6, 8, 10) THEN cost_score / 2
                ELSE cost_score
              END
            """
        )
    )
