from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamped, UUIDPrimaryKey, domain_enum
from app.shared.enums import (
    ApplicationSource,
    CommunicationChannel,
    EmploymentType,
    HiringStage,
    Outcome,
    RoleCategory,
    SilenceSeverity,
    StageEventType,
    VerificationStatus,
)


class RecruitmentExperience(UUIDPrimaryKey, Timestamped, Base):
    """One applicant's structured record of one hiring process.

    Public surfaces render the structured fields only. `user_id` is never
    exposed — not in public APIs, and not to a company in a dispute
    (docs/08 §4).
    """

    __tablename__ = "recruitment_experiences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )

    role_title: Mapped[str] = mapped_column(String(120), nullable=False)
    role_category: Mapped[RoleCategory] = mapped_column(
        domain_enum(RoleCategory, "role_category"), nullable=False
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        domain_enum(EmploymentType, "employment_type"), nullable=False
    )
    source: Mapped[ApplicationSource] = mapped_column(
        domain_enum(ApplicationSource, "application_source"), nullable=False
    )

    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    furthest_stage: Mapped[HiringStage] = mapped_column(
        domain_enum(HiringStage, "hiring_stage"), nullable=False
    )

    last_company_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    promised_result: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    promised_result_date: Mapped[date | None] = mapped_column(Date)
    promised_window_end_date: Mapped[date | None] = mapped_column(Date)

    result_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_channel: Mapped[CommunicationChannel | None] = mapped_column(
        domain_enum(CommunicationChannel, "communication_channel")
    )

    outcome: Mapped[Outcome] = mapped_column(
        domain_enum(Outcome, "outcome"),
        default=Outcome.UNKNOWN,
        nullable=False,
    )

    # Structured tags come first; free text is short, optional, and moderated.
    context_tags: Mapped[list[str]] = mapped_column(JSONB, server_default="[]", nullable=False)
    free_context: Mapped[str | None] = mapped_column(String(500))

    verification_status: Mapped[VerificationStatus] = mapped_column(
        domain_enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.DRAFT,
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Computed at submit under a known methodology version, so a later
    # threshold change never silently rewrites history.
    severity: Mapped[SilenceSeverity] = mapped_column(
        domain_enum(SilenceSeverity, "silence_severity"),
        default=SilenceSeverity.L0_INSUFFICIENT,
        nullable=False,
    )
    methodology_version: Mapped[str | None] = mapped_column(String(32))

    # Duplicate detection: hash of (user, company, stage, application month).
    dedupe_hash: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(80))

    helpful_count: Mapped[int] = mapped_column(default=0, nullable=False)

    auto_check_flags: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )

    stage_events: Mapped[list[RecruitmentStageEvent]] = relationship(
        back_populates="experience", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "NOT promised_result OR promised_result_date IS NOT NULL"
            " OR promised_window_end_date IS NOT NULL",
            name="promise_needs_a_date",
        ),
        CheckConstraint(
            "NOT result_received OR result_received_at IS NOT NULL",
            name="received_result_needs_timestamp",
        ),
        # The company page query: verified reports for one company, newest first.
        Index(
            "ix_experiences_company_status_date",
            "company_id",
            "verification_status",
            "application_date",
        ),
        Index("ix_experiences_user_created", "user_id", "created_at"),
        Index("ix_experiences_dedupe", "dedupe_hash"),
        Index(
            "uq_experiences_user_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_experiences_company_stage", "company_id", "furthest_stage"),
    )


class RecruitmentStageEvent(Base):
    """Precise timeline entries behind an experience. These render as the
    public Ghostory without ever naming the reporter."""

    __tablename__ = "recruitment_stage_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruitment_experiences.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[StageEventType] = mapped_column(
        domain_enum(StageEventType, "stage_event_type"), nullable=False
    )
    stage: Mapped[HiringStage | None] = mapped_column(domain_enum(HiringStage, "hiring_stage"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[CommunicationChannel | None] = mapped_column(
        domain_enum(CommunicationChannel, "communication_channel")
    )
    note: Mapped[str | None] = mapped_column(Text)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    experience: Mapped[RecruitmentExperience] = relationship(back_populates="stage_events")

    __table_args__ = (Index("ix_stage_events_experience_time", "experience_id", "occurred_at"),)
