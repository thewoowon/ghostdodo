from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamped, UUIDPrimaryKey, domain_enum
from app.shared.enums import CompanyClaimState, CompanySizeBand


class Company(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "companies"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    legal_name_ko: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name_ko: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))

    # Korean company search: users type "카카오", "kakao", "(주)카카오", or a
    # former name. Aliases are matched alongside the canonical names.
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), server_default="{}", nullable=False
    )

    industry: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(String(500))
    size_band: Mapped[CompanySizeBand] = mapped_column(
        domain_enum(CompanySizeBand, "company_size_band"),
        default=CompanySizeBand.UNKNOWN,
        nullable=False,
    )

    claim_state: Mapped[CompanyClaimState] = mapped_column(
        domain_enum(CompanyClaimState, "company_claim_state"),
        default=CompanyClaimState.UNCLAIMED,
        nullable=False,
    )

    # Fixtures are labelled so demo numbers can never be mistaken for real
    # observations about a real employer (docs/10 seed data rule).
    is_demo: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    # Directory provenance. Company NAMES may come from lawful public
    # registries; response METRICS may not — they require qualified user
    # reports. Recording where a record came from keeps that line auditable.
    directory_source: Mapped[str | None] = mapped_column(String(20))
    directory_ref: Mapped[str | None] = mapped_column(String(64))
    directory_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Aggressively normalized name used only for import dedupe, never shown.
    # Without it the same employer imports as several companies and each one
    # stays under the publishable sample bar forever.
    match_key: Mapped[str | None] = mapped_column(String(200))

    # Denormalized counter for search ranking and list cards. Not a metric.
    public_report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        # Trigram indexes for typo-tolerant Korean search; created alongside
        # the pg_trgm extension in the initial migration.
        Index(
            "ix_companies_display_name_trgm",
            "display_name_ko",
            postgresql_using="gin",
            postgresql_ops={"display_name_ko": "gin_trgm_ops"},
        ),
        Index(
            "ix_companies_legal_name_trgm",
            "legal_name_ko",
            postgresql_using="gin",
            postgresql_ops={"legal_name_ko": "gin_trgm_ops"},
        ),
        Index("ix_companies_aliases_gin", "aliases", postgresql_using="gin"),
        Index("ix_companies_report_count", "public_report_count"),
        Index(
            "uq_companies_match_key",
            "match_key",
            unique=True,
            postgresql_where=text("match_key IS NOT NULL"),
        ),
        Index("ix_companies_directory_ref", "directory_source", "directory_ref"),
    )


class CompanyAddRequest(Base):
    """A contributor hit a company we don't have. Reviewed before it becomes
    a searchable Company, so the directory can't be spammed into existence."""

    __tablename__ = "company_add_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column()
    submitted_name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    resolved_company_id: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_company_add_requests_status", "status"),)
