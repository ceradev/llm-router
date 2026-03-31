"""add session_id to llm_requests

Revision ID: f1a2b3c4d5e6
Revises: e8f3a1b2c4d5
Create Date: 2026-03-29

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8f3a1b2c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_requests",
        sa.Column("session_id", sa.String(length=128), nullable=True),
    )
    op.create_index(op.f("ix_llm_requests_session_id"), "llm_requests", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_requests_session_id"), table_name="llm_requests")
    op.drop_column("llm_requests", "session_id")
