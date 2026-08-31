from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, domain_enum
from app.shared.enums import CreditEventType, ReputationEventType


class ReputationEvent(Base):
    """Immutable reputation ledger.

    A reversal is recorded as a new negative-delta row, never by editing or
    deleting history — the ledger has to stay auditable (docs/09 Phase 4).
    """

    __tablename__ = "reputation_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[ReputationEventType] = mapped_column(
        domain_enum(ReputationEventType, "reputation_event_type"), nullable=False
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    subject_type: Mapped[str | None] = mapped_column(String(60))
    subject_id: Mapped[uuid.UUID | None] = mapped_column()

    # Set on reversals so an award and its undo can be paired in an audit.
    reverses_event_id: Mapped[uuid.UUID | None] = mapped_column()

    # Guards against double-awarding the same (user, event, subject) triple.
    dedupe_key: Mapped[str | None] = mapped_column(String(120))

    detail: Mapped[dict[str, object]] = mapped_column(JSONB, server_default="{}", nullable=False)
    # clock_timestamp(), not now(): now() returns the transaction start time,
    # so every ledger row written in one transaction would share a timestamp
    # and the append-only history could not be ordered. clock_timestamp()
    # advances within the transaction, keeping the sequence reconstructable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_reputation_dedupe_key"),
        Index("ix_reputation_user_time", "user_id", "created_at"),
    )


class CreditLedger(Base):
    """Immutable Dodo Credit ledger. Product utility only — never cash,
    never transferable, no speculative framing (docs/07 §1)."""

    __tablename__ = "credit_ledger"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[CreditEventType] = mapped_column(
        domain_enum(CreditEventType, "credit_event_type"), nullable=False
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    subject_type: Mapped[str | None] = mapped_column(String(60))
    subject_id: Mapped[uuid.UUID | None] = mapped_column()
    dedupe_key: Mapped[str | None] = mapped_column(String(120))

    memo: Mapped[str | None] = mapped_column(String(200))
    # clock_timestamp(), not now(): now() returns the transaction start time,
    # so every ledger row written in one transaction would share a timestamp
    # and the append-only history could not be ordered. clock_timestamp()
    # advances within the transaction, keeping the sequence reconstructable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_credit_dedupe_key"),
        Index("ix_credit_user_time", "user_id", "created_at"),
    )


class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    badge_code: Mapped[str] = mapped_column(String(60), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),
        Index("ix_user_badges_user", "user_id"),
    )
