from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api_deps import DbSession, OptionalUser, client_ip
from app.core import rate_limit
from app.core.config import settings
from app.core.security import hash_ip
from app.modules.jobs import service
from app.modules.jobs.schemas import JobCard, JobDetail, OutboundClickAccepted
from app.shared.errors import FeatureDisabledError
from app.shared.schemas import Page


async def require_jobs_enabled() -> None:
    """Jobs ship behind a flag so the surface can be closed without a deploy.

    Closed reads as 404, not 403 — a feature that is not open should not
    advertise that it exists.
    """
    if not settings.enable_jobs:
        raise FeatureDisabledError()


router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_jobs_enabled)])


class OutboundClickInput(BaseModel):
    """Where on the site the click happened, so the funnel can separate a
    company page from the jobs index. Anything that is not a same-site path
    is discarded server-side."""

    referrer_path: str | None = Field(default=None, max_length=service.MAX_REFERRER_PATH)


@router.get("", response_model=Page[JobCard])
async def list_jobs(
    db: DbSession,
    company: Annotated[uuid.UUID | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[JobCard]:
    """Open postings only. A closed one still resolves by id, so a shared
    link explains itself rather than 404ing."""
    page = await service.list_jobs(db, company_id=company, query=q, cursor=cursor, limit=limit)
    return Page(
        items=[JobCard.of(row.job, row.company) for row in page.rows],
        next_cursor=page.next_cursor,
    )


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: uuid.UUID, db: DbSession) -> JobDetail:
    row = await service.get_job(db, job_id)
    return JobDetail.of(row.job, row.company)


@router.post("/{job_id}/outbound-click", response_model=OutboundClickAccepted)
async def outbound_click(
    job_id: uuid.UUID,
    payload: OutboundClickInput,
    request: Request,
    db: DbSession,
    user: OptionalUser,
) -> OutboundClickAccepted:
    """Counts a `지원하러 가기` click and hands back the deep link.

    The client links straight to the employer — this call is accounting, not
    a redirect, so a failure here must never stop someone from applying. The
    row stores a salted visitor hash rather than an IP (docs/08 §9).
    """
    row = await service.get_job(db, job_id)
    apply_url = JobDetail.of(row.job, row.company).apply_url
    if apply_url is None:
        raise FeatureDisabledError("이 공고는 지원 링크를 확인할 수 없습니다.")

    visitor_hash = hash_ip(client_ip(request))
    await rate_limit.enforce(
        "outbound_click",
        str(user.id) if user else (visitor_hash or "anon"),
        rate_limit.OUTBOUND_CLICK,
    )

    recorded = await service.record_outbound_click(
        db,
        job=row.job,
        user_id=user.id if user else None,
        visitor_hash=visitor_hash,
        referrer_path=service.clean_referrer_path(payload.referrer_path),
    )
    await db.commit()
    return OutboundClickAccepted(apply_url=apply_url, recorded=recorded)
