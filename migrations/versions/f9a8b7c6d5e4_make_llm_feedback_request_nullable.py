"""Make llm_feedback.request_id nullable.

Revision ID: f9a8b7c6d5e4
Revises: e5f6a7b8c9d0
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9a8b7c6d5e4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str | Sequence[str] | None] = None
depends_on: Union[str | Sequence[str] | None] = None


def upgrade() -> None:
    op.alter_column(
        "llm_feedback",
        "request_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "llm_feedback",
        "request_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
