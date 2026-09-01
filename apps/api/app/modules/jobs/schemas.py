from __future__ import annotations

import uuid
from datetime import date, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.modules.companies.models import Company
from app.modules.companies.schemas import CompanySummary
from app.modules.jobs.models import JobPosting
from app.shared.enums import ApplicationSource, EmploymentType, RoleCategory

SEOUL = ZoneInfo("Asia/Seoul")
"""Closing dates are Korean calendar dates; comparing them against a UTC date
would close a posting up to nine hours early."""

_APPLY_SCHEMES = frozenset({"http", "https"})


def safe_apply_url(raw: str) -> str | None:
    """The deep-link target, or None when it cannot be safely linked.

    A posting URL is written by an importer or a moderator, not by the
    renderer, so it reaches an `href` as data. Anything but http(s) — a
    `javascript:` or `data:` URL above all — is dropped rather than emitted,
    because the client has no way to tell a bad one from a good one.
    """
    try:
        parts = urlsplit(raw.strip())
    except ValueError:
        return None
    if parts.scheme.lower() not in _APPLY_SCHEMES or not parts.netloc:
        return None
    return raw.strip()


def today_seoul() -> date:
    return datetime.now(SEOUL).date()


class JobCard(BaseModel):
    """A linked posting. GhostDodo never hosts an application — every card
    is an outbound deep link, and the source it came from stays visible on it
    (docs/09 Phase 6 acceptance)."""

    id: uuid.UUID
    title: str
    role_category: RoleCategory | None
    employment_type: EmploymentType | None
    location: str | None
    source: ApplicationSource
    source_label: str | None
    closes_on: date | None
    is_open: bool
    observed_at: datetime
    #: None when the stored URL is not a linkable http(s) address. The UI
    #: shows the posting without an apply CTA rather than a dead link.
    apply_url: str | None
    company: CompanySummary

    @classmethod
    def of(cls, job: JobPosting, company: Company, *, today: date | None = None) -> JobCard:
        return cls(
            id=job.id,
            title=job.title,
            role_category=job.role_category,
            employment_type=job.employment_type,
            location=job.location,
            source=job.source,
            source_label=job.source_label,
            closes_on=job.closes_on,
            is_open=is_open(job, today=today),
            observed_at=job.observed_at,
            apply_url=safe_apply_url(job.source_url),
            company=CompanySummary.model_validate(company),
        )


class JobDetail(JobCard):
    last_checked_at: datetime | None

    @classmethod
    def of(cls, job: JobPosting, company: Company, *, today: date | None = None) -> JobDetail:
        card = JobCard.of(job, company, today=today)
        return cls(**card.model_dump(), last_checked_at=job.last_checked_at)


class OutboundClickAccepted(BaseModel):
    """Confirms the click was counted and echoes where the client should go.

    The client already holds `apply_url`; returning it means a caller that
    posts first and navigates second never has to trust its own stale copy.
    """

    apply_url: str
    recorded: bool


def is_open(job: JobPosting, *, today: date | None = None) -> bool:
    """A posting is open until it is deactivated or its closing date passes.

    Expiry is derived, not stored, so a posting closes on schedule without a
    job runner having to sweep the table (docs/09 Phase 6: expired links
    manageable).
    """
    if not job.is_active:
        return False
    if job.closes_on is None:
        return True
    return job.closes_on >= (today or today_seoul())
