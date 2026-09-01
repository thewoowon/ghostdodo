"""users.google_sub for Google sign-in

Revision ID: 8c1e5a4d9b73
Revises: 3f4cdcc8182c
Create Date: 2026-08-31 18:30:00.000000+00:00

Nullable on purpose: accounts created through the magic link have no Google
subject, and both providers converge on the same row by verified email.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c1e5a4d9b73"
down_revision: str | None = "3f4cdcc8182c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=64), nullable=True))
    op.create_unique_constraint(op.f("uq_users_google_sub"), "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users_google_sub"), "users", type_="unique")
    op.drop_column("users", "google_sub")
