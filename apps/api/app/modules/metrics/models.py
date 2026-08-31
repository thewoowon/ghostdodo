from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, domain_enum
from app.shared.enums import MetricEligibility, MetricWindow


class CompanyMetricSnapshot(Base):
    """Precomputed company aggregates.

    Company pages read these rows; they never aggregate raw reports per
    request (docs/05 §7). Recomputed when a report's verification status
    changes, and on a schedule so time-based windows stay current.
    """

    __tablename__ = "company_metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    window: Mapped[MetricWindow] = mapped_column(
        domain_enum(MetricWindow, "metric_window"), nullable=False
    )
    window_start: Mapped[date | None] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)

    qualified_n: Mapped[int] = mapped_column(Integer, nullable=False)
    verified_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    response_rate: Mapped[float | None] = mapped_column(Float)
    ghost_rate: Mapped[float | None] = mapped_column(Float)
    broken_promise_rate: Mapped[float | None] = mapped_column(Float)
    median_response_days: Mapped[float | None] = mapped_column(Float)
    promised_timeline_n: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    eligibility: Mapped[MetricEligibility] = mapped_column(
        domain_enum(MetricEligibility, "metric_eligibility"), nullable=False
    )

    # {stage: {qualified_n, response_rate, ghost_rate, median_response_days}}
    stage_breakdown: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )

    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("company_id", "window", name="uq_metric_snapshot_company_window"),
        Index("ix_metric_snapshots_company", "company_id"),
        # Powers /dex leaderboards without touching raw reports.
        Index("ix_metric_snapshots_window_eligibility", "window", "eligibility"),
        Index("ix_metric_snapshots_window_response", "window", "response_rate"),
    )
