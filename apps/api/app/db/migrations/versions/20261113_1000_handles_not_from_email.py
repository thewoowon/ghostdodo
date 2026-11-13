"""rename handles that were derived from the email address

Revision ID: b6f2d9e1c4a8
Revises: 8c1e5a4d9b73
Create Date: 2026-11-13 10:00:00.000000+00:00

Handles used to be `<email local part>_<6 hex>`, which published the local
part of every user's address while the privacy policy promised a handle
could not be inferred from it. New handles are `dodo_<8 hex>`; this renames
every account still in the old shape. The old form is the only one that
matches the pattern below: seeded handles are Korean and the new form
carries eight hex digits.

Not reversible: the old handles are the leak being removed.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b6f2d9e1c4a8"
down_revision: str | None = "8c1e5a4d9b73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        r"""
        UPDATE users
        SET handle = 'dodo_' || substr(md5(random()::text || id::text), 1, 8)
        WHERE handle ~ '^[a-z0-9]{1,16}_[0-9a-f]{6}$'
        """
    )


def downgrade() -> None:
    pass
