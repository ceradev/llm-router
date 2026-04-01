"""Trim accidental leading slash from openrouter_model_id.

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-03-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE llm_models
            SET openrouter_model_id = LTRIM(openrouter_model_id, '/')
            WHERE openrouter_model_id LIKE '/%'
            """
        )
    )


def downgrade() -> None:
    # Data correction only; do not reintroduce malformed leading slashes.
    pass
