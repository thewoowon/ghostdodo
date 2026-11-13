"""quick-log batches on recruitment experiences

Revision ID: e8b4f2a6c9d1
Revises: d3a7c1f0e5b2
Create Date: 2026-11-13 22:00:00.000000+00:00

Reports filed together through the quick log share a batch id, so the
moderator queue can review them as one submission.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8b4f2a6c9d1"
down_revision: str | None = "d3a7c1f0e5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("recruitment_experiences", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_experiences_batch",
        "recruitment_experiences",
        ["batch_id"],
        unique=False,
        postgresql_where=sa.text("batch_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_experiences_batch", table_name="recruitment_experiences")
    op.drop_column("recruitment_experiences", "batch_id")
