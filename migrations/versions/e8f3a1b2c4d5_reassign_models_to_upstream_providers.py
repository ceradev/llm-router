"""reassign llm_models from openrouter catalog to upstream provider slugs

Revision ID: e8f3a1b2c4d5
Revises: d954d9a49510
Create Date: 2026-03-29

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f3a1b2c4d5"
down_revision: Union[str, Sequence[str], None] = "d954d9a49510"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _display_name_for_slug(slug: str) -> str:
    return slug.replace("-", " ").title()[:128]


def _ensure_provider_id(conn: sa.Connection, *, slug: str, cache: dict[str, int]) -> int:
    if slug in cache:
        return cache[slug]
    row = conn.execute(sa.text("SELECT id FROM providers WHERE slug = :slug"), {"slug": slug}).fetchone()
    if row is not None:
        pid = int(row[0])
        cache[slug] = pid
        return pid
    dn = _display_name_for_slug(slug)
    ins = conn.execute(
        sa.text(
            """
            INSERT INTO providers (slug, display_name, api_base_url, is_active, created_at, updated_at)
            VALUES (:slug, :dn, NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"slug": slug, "dn": dn},
    )
    out = ins.fetchone()
    if out is None:
        raise RuntimeError(f"Failed to insert provider {slug}")
    pid = int(out[0])
    cache[slug] = pid
    return pid


def _parse_upstream_from_routing_key(routing_key: str) -> tuple[str, str] | None:
    prefix = "openrouter/"
    if not routing_key.startswith(prefix):
        return None
    full_id = routing_key[len(prefix) :].strip()
    if not full_id:
        return None
    parts = full_id.split("/", 1)
    if len(parts) < 2:
        slug = parts[0].strip()
        return (slug, full_id[:255]) if slug else None
    return (parts[0].strip(), parts[1].strip()[:255])


def _fallback_from_external(external_model_id: str) -> tuple[str, str] | None:
    parts = external_model_id.split("/", 1)
    if len(parts) < 2:
        return None
    return (parts[0].strip(), parts[1].strip()[:255])


def upgrade() -> None:
    conn = op.get_bind()
    if conn is None:
        return

    row = conn.execute(sa.text("SELECT id FROM providers WHERE slug = 'openrouter'")).fetchone()
    if row is None:
        return
    openrouter_id = int(row[0])

    rows = conn.execute(
        sa.text(
            "SELECT id, routing_key, external_model_id FROM llm_models WHERE provider_id = :pid"
        ),
        {"pid": openrouter_id},
    ).fetchall()

    if not rows:
        return

    cache: dict[str, int] = {}
    for mid, routing_key, external_model_id in rows:
        parsed = _parse_upstream_from_routing_key(str(routing_key))
        if parsed is None:
            fb = _fallback_from_external(str(external_model_id))
            if fb is None:
                continue
            slug, suffix = fb
        else:
            slug, suffix = parsed
        if not slug or not suffix:
            continue

        pid = _ensure_provider_id(conn, slug=slug, cache=cache)
        conn.execute(
            sa.text(
                """
                UPDATE llm_models
                SET provider_id = :pid, external_model_id = :ext, updated_at = now()
                WHERE id = :mid
                """
            ),
            {"pid": pid, "ext": suffix, "mid": int(mid)},
        )


def downgrade() -> None:
    """Data migration is not reversed: upstream provider rows may be shared."""
