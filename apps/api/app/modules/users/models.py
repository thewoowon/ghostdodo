from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamped, UUIDPrimaryKey, domain_enum
from app.shared.enums import ReputationRank, TrustState, UserRole


class User(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "users"

    # Public pseudonym. Real identity is never required to be public (docs/07 §6).
    handle: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Google's stable subject id. Matched before email, because a Google
    # account's address can change while `sub` never does — keying only on
    # email would hand the account to whoever inherits the old address.
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)

    role: Mapped[UserRole] = mapped_column(
        domain_enum(UserRole, "user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    trust_state: Mapped[TrustState] = mapped_column(
        domain_enum(TrustState, "trust_state"),
        default=TrustState.NEW,
        nullable=False,
    )

    # Denormalized running totals. The ledgers in modules.reputation are the
    # source of truth; these exist so profile reads stay a single row.
    reputation_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[ReputationRank] = mapped_column(
        domain_enum(ReputationRank, "reputation_rank"),
        default=ReputationRank.OBSERVER,
        nullable=False,
    )

    verified_contribution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reversed_contribution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    bio: Mapped[str | None] = mapped_column(Text)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_users_role", "role"),)


class MagicLinkToken(Base):
    """Single-use email sign-in token. Only the hash is stored, so a database
    read cannot be replayed as a login."""

    __tablename__ = "magic_link_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_ip_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (Index("ix_magic_link_email_expires", "email", "expires_at"),)


class SavedCompany(Base):
    __tablename__ = "saved_companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_saved_company_user_company"),
        Index("ix_saved_companies_user", "user_id"),
    )
