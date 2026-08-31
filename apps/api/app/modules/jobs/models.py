from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, domain_enum
from app.shared.enums import ApplicationSource, EmploymentType, RoleCategory


class JobPosting(Base):
    """MVP is deep-link only: GhostDodo links out to the employer or job
    board and records the outbound click. It never hosts an application."""

    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    role_category: Mapped[RoleCategory | None] = mapped_column(
        domain_enum(RoleCategory, "role_category")
    )
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        domain_enum(EmploymentType, "employment_type")
    )
    location: Mapped[str | None] = mapped_column(String(120))

    source: Mapped[ApplicationSource] = mapped_column(
        domain_enum(ApplicationSource, "application_source"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    # Source attribution must stay visible on the card (docs/09 Phase 6).
    source_label: Mapped[str | None] = mapped_column(String(80))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    closes_on: Mapped[date | None] = mapped_column(Date)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("company_id", "source_url", name="uq_job_company_source_url"),
        Index("ix_jobs_company_active", "company_id", "is_active"),
    )


class OutboundClick(Base):
    """Aggregate funnel analytics. Deliberately stores no raw IP — a salted
    hash is enough to deduplicate without building a browsing profile."""

    __tablename__ = "outbound_clicks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    visitor_hash: Mapped[str | None] = mapped_column(String(64))
    referrer_path: Mapped[str | None] = mapped_column(String(300))
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_outbound_job_time", "job_id", "clicked_at"),)
