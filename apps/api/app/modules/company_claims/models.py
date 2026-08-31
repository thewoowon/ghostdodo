from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyClaim(Base):
    """Representative access request. Requires proof of company domain or
    authority; being claimed never grants the right to remove reports
    (docs/08 §6)."""

    __tablename__ = "company_claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    claimant_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    work_email: Mapped[str] = mapped_column(String(320), nullable=False)
    work_email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role_title: Mapped[str | None] = mapped_column(String(120))
    evidence_note: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decision_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_claims_company_status", "company_id", "status"),)


class CorrectionRequest(Base):
    """A factual challenge to a record. Challenges the RECORD, never the
    reporter: the reporter's identity is not disclosed at any point in this
    workflow (docs/08 §4-5)."""

    __tablename__ = "correction_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recruitment_experiences.id", ondelete="SET NULL")
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    contact_email: Mapped[str | None] = mapped_column(String(320))

    claim_summary: Mapped[str] = mapped_column(Text, nullable=False)
    disputed_fields: Mapped[list[str]] = mapped_column(JSONB, server_default="[]", nullable=False)
    supporting_note: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(40))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_corrections_status_created", "status", "created_at"),
        Index("ix_corrections_company", "company_id"),
    )


class CompanyStatement(Base):
    """A bounded official statement shown on the company page. Length-capped
    so it stays a response, not an ad."""

    __tablename__ = "company_statements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(String(1200), nullable=False)
    is_published: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_statements_company_published", "company_id", "is_published"),)
