"""Linked job postings and outbound click accounting.

Two things this module deliberately does not do: host an application, and
build a browsing profile. A posting is a link out, and a click is an
aggregate counter — the row carries a salted visitor hash and a same-site
path, never a raw IP and never a full referring URL.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company
from app.modules.companies.service import normalize_company_query
from app.modules.jobs.models import JobPosting, OutboundClick
from app.modules.jobs.schemas import today_seoul
from app.shared.errors import JobNotFoundError

CLICK_DEDUPE_WINDOW = timedelta(minutes=30)
"""Repeat clicks from one visitor on one posting inside this window count
once. A double-click, a back-button, and an opened-then-closed tab are the
same intent, and counting them separately would inflate apply CTR — a launch
metric (docs/09), so it has to mean something."""

MAX_REFERRER_PATH = 300


@dataclass(frozen=True, slots=True)
class JobRow:
    job: JobPosting
    company: Company


@dataclass(frozen=True, slots=True)
class JobPage:
    rows: list[JobRow]
    next_cursor: str | None


def _encode_cursor(observed_at: datetime, job_id: uuid.UUID) -> str:
    raw = f"{observed_at.isoformat()}|{job_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    """Returns None for anything unparseable.

    A cursor is an opaque token a client copies around; a mangled one should
    restart the listing, not 500.
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        observed_at, _, job_id = raw.partition("|")
        return datetime.fromisoformat(observed_at), uuid.UUID(job_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None


def _open_postings_only(
    stmt: Select[tuple[JobPosting, Company]], today: date
) -> Select[tuple[JobPosting, Company]]:
    """Expired links are excluded from listings but still resolve by id, so a
    bookmarked or shared posting explains that it closed instead of 404ing."""
    return stmt.where(
        JobPosting.is_active.is_(True),
        or_(JobPosting.closes_on.is_(None), JobPosting.closes_on >= today),
    )


async def list_jobs(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    query: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    today: date | None = None,
) -> JobPage:
    stmt = select(JobPosting, Company).join(Company, Company.id == JobPosting.company_id)
    stmt = _open_postings_only(stmt, today or today_seoul())

    if company_id is not None:
        stmt = stmt.where(JobPosting.company_id == company_id)

    if query:
        normalized = normalize_company_query(query)
        if normalized:
            like = f"%{normalized}%"
            stmt = stmt.where(
                or_(
                    JobPosting.title.ilike(like),
                    JobPosting.location.ilike(like),
                    Company.display_name_ko.ilike(like),
                )
            )

    # Newest observation first, with the id as a deterministic tiebreak — two
    # postings imported in one batch share a timestamp, and without the
    # tiebreak the keyset cursor could skip or repeat one of them.
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded is not None:
            observed_at, job_id = decoded
            stmt = stmt.where(
                or_(
                    JobPosting.observed_at < observed_at,
                    (JobPosting.observed_at == observed_at) & (JobPosting.id < job_id),
                )
            )

    stmt = stmt.order_by(JobPosting.observed_at.desc(), JobPosting.id.desc()).limit(limit + 1)

    result = (await session.execute(stmt)).all()
    has_more = len(result) > limit
    page = result[:limit]
    rows = [JobRow(job=job, company=company) for job, company in page]
    next_cursor = (
        _encode_cursor(rows[-1].job.observed_at, rows[-1].job.id) if has_more and rows else None
    )
    return JobPage(rows=rows, next_cursor=next_cursor)


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> JobRow:
    row = (
        await session.execute(
            select(JobPosting, Company)
            .join(Company, Company.id == JobPosting.company_id)
            .where(JobPosting.id == job_id)
        )
    ).first()
    if row is None:
        raise JobNotFoundError()
    job, company = row
    return JobRow(job=job, company=company)


def clean_referrer_path(raw: str | None) -> str | None:
    """Keeps a same-site path and nothing else.

    The client sends where the click came from so the funnel can tell a
    company page from the jobs index. A full URL — or any absolute or
    protocol-relative reference — would carry an external origin into the
    analytics table, so only a rooted path survives.
    """
    if not raw:
        return None
    path = raw.strip()
    if not path.startswith("/") or path.startswith("//"):
        return None
    return path[:MAX_REFERRER_PATH]


async def record_outbound_click(
    session: AsyncSession,
    *,
    job: JobPosting,
    user_id: uuid.UUID | None,
    visitor_hash: str | None,
    referrer_path: str | None,
    now: datetime | None = None,
) -> bool:
    """Appends a click unless the same visitor already counted recently.

    Returns whether a row was written — the caller answers the same way
    either way, so a deduplicated click is never an error to the user.
    """
    moment = now or datetime.now(UTC)
    identity = visitor_hash
    if user_id is not None or identity is not None:
        recent = (
            await session.execute(
                select(OutboundClick.id)
                .where(
                    OutboundClick.job_id == job.id,
                    OutboundClick.clicked_at >= moment - CLICK_DEDUPE_WINDOW,
                    (OutboundClick.user_id == user_id)
                    if user_id is not None
                    else (OutboundClick.visitor_hash == identity),
                )
                .limit(1)
            )
        ).first()
        if recent is not None:
            return False

    session.add(
        OutboundClick(
            job_id=job.id,
            user_id=user_id,
            visitor_hash=visitor_hash,
            referrer_path=referrer_path,
        )
    )
    await session.flush()
    return True
