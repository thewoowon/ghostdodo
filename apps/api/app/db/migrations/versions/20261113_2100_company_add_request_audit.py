"""audit action for company add-request decisions

Revision ID: d3a7c1f0e5b2
Revises: b6f2d9e1c4a8
Create Date: 2026-11-13 21:00:00.000000+00:00

Moderators now approve, merge, or reject requests to add a company, and
every moderator action is audit-logged.

Not reversible: Postgres cannot drop a value from an enum type, and the rows
that use it are append-only audit history.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d3a7c1f0e5b2"
down_revision: str | None = "b6f2d9e1c4a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'COMPANY_ADD_REQUEST_DECISION'")


def downgrade() -> None:
    pass
