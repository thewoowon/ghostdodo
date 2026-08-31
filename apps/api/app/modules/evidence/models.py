from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, domain_enum
from app.shared.enums import EvidenceAccessState, EvidenceReviewState


class Evidence(Base):
    """Moderation material, not a public post.

    `object_key` must never leave the server through a public serializer —
    see `app.modules.evidence.schemas`, which has no field for it.
    """

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruitment_experiences.id", ondelete="CASCADE"), nullable=False
    )

    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    original_filename: Mapped[str | None] = mapped_column(String(255))

    kind: Mapped[str] = mapped_column(String(40), nullable=False, server_default="OTHER")

    review_state: Mapped[EvidenceReviewState] = mapped_column(
        domain_enum(EvidenceReviewState, "evidence_review_state"),
        default=EvidenceReviewState.PENDING,
        nullable=False,
    )
    access_state: Mapped[EvidenceAccessState] = mapped_column(
        domain_enum(EvidenceAccessState, "evidence_access_state"),
        default=EvidenceAccessState.UPLOAD_PENDING,
        nullable=False,
    )
    pii_notes: Mapped[str | None] = mapped_column(Text)

    # clock_timestamp(), not now(): now() returns the transaction start time,
    # so every ledger row written in one transaction would share a timestamp
    # and the append-only history could not be ordered. clock_timestamp()
    # advances within the transaction, keeping the sequence reconstructable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_evidence_experience", "experience_id"),
        # Identical files across many "independent" reports is a brigading
        # signal (docs/08 §7).
        Index("ix_evidence_sha256", "sha256"),
    )


class EvidenceAccessLog(Base):
    """Append-only. Every moderator view of private evidence is recorded."""

    __tablename__ = "evidence_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    accessed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("ix_evidence_access_evidence_time", "evidence_id", "accessed_at"),
        Index("ix_evidence_access_user_time", "accessed_by_user_id", "accessed_at"),
    )
