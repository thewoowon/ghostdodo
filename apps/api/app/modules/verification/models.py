from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, domain_enum
from app.shared.enums import AuditAction, ReviewDecision, VerificationStatus


class VerificationReview(Base):
    """A moderator decision on one report. Append-only: a later reversal is a
    new row, so the review history stays reconstructable."""

    __tablename__ = "verification_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruitment_experiences.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    decision: Mapped[ReviewDecision] = mapped_column(
        domain_enum(ReviewDecision, "review_decision"), nullable=False
    )
    status_before: Mapped[VerificationStatus] = mapped_column(
        domain_enum(VerificationStatus, "verification_status"), nullable=False
    )
    status_after: Mapped[VerificationStatus] = mapped_column(
        domain_enum(VerificationStatus, "verification_status"), nullable=False
    )

    reasons: Mapped[list[str]] = mapped_column(JSONB, server_default="[]", nullable=False)
    structured_checks: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)

    # clock_timestamp(), not now(): now() returns the transaction start time,
    # so every ledger row written in one transaction would share a timestamp
    # and the append-only history could not be ordered. clock_timestamp()
    # advances within the transaction, keeping the sequence reconstructable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("ix_reviews_experience_time", "experience_id", "created_at"),
        Index("ix_reviews_reviewer_time", "reviewer_id", "created_at"),
    )


class AuditLog(Base):
    """Append-only audit trail (docs/05 §8). No update or delete path exists
    in application code; retention is handled operationally."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[AuditAction] = mapped_column(
        domain_enum(AuditAction, "audit_action"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    subject_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column()
    request_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, server_default="{}", nullable=False)
    # clock_timestamp(), not now(): now() returns the transaction start time,
    # so every ledger row written in one transaction would share a timestamp
    # and the append-only history could not be ordered. clock_timestamp()
    # advances within the transaction, keeping the sequence reconstructable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_subject", "subject_type", "subject_id", "created_at"),
        Index("ix_audit_action_time", "action", "created_at"),
    )
