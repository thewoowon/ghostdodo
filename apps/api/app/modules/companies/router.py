from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app.api_deps import DbSession, OptionalUser, client_ip
from app.core import rate_limit
from app.core.methodology import get_methodology
from app.core.security import hash_ip
from app.modules.companies import service
from app.modules.companies.schemas import (
    CompanyAddRequestAccepted,
    CompanyAddRequestInput,
    CompanyDetail,
    CompanySummary,
    publishes,
)
from app.modules.jobs import service as jobs_service
from app.modules.jobs.router import require_jobs_enabled
from app.modules.jobs.schemas import JobCard
from app.modules.metrics.schemas import CompanyMetricsOut
from app.modules.metrics.service import get_snapshot
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.schemas import PublicReportCard
from app.shared.enums import PUBLIC_REPORT_STATUSES, MetricWindow
from app.shared.schemas import Page

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/search", response_model=list[CompanySummary])
async def search(
    request: Request,
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CompanySummary]:
    identity = hash_ip(client_ip(request)) or "anon"
    await rate_limit.enforce("company_search", identity, rate_limit.SEARCH)
    companies = await service.search_companies(db, query=q, limit=limit)
    return [CompanySummary.model_validate(c) for c in companies]


@router.get("/{slug}", response_model=CompanyDetail)
async def detail(slug: str, db: DbSession) -> CompanyDetail:
    company = await service.get_company_by_slug(db, slug)
    return CompanyDetail.model_validate(company)


@router.get("/{slug}/metrics", response_model=CompanyMetricsOut)
async def metrics(
    slug: str,
    db: DbSession,
    window: Annotated[MetricWindow, Query()] = MetricWindow.W12M,
) -> CompanyMetricsOut:
    """Serves a precomputed snapshot. When a company has no snapshot yet the
    response is an explicit insufficient-data shape — never a zeroed one,
    which would read as '0% response rate'."""
    company = await service.get_company_by_slug(db, slug)
    methodology = get_methodology()
    if not publishes(company.is_demo):
        return CompanyMetricsOut.withheld_for(
            company_id=company.id, window=window, methodology_version=methodology.version
        )
    snapshot = await get_snapshot(db, company.id, window)
    if snapshot is None:
        return CompanyMetricsOut.empty(
            company_id=company.id, window=window, methodology_version=methodology.version
        )
    return CompanyMetricsOut.from_snapshot(snapshot)


@router.get("/{slug}/reports", response_model=list[PublicReportCard])
async def reports(
    slug: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[PublicReportCard]:
    """Only publicly-visible statuses, and never the reporter. Nothing at all
    for a company the launch gate holds back: a verified card is published
    the moment it is verified, with no sample bar in between."""
    company = await service.get_company_by_slug(db, slug)
    if not publishes(company.is_demo):
        return []
    rows = await db.execute(
        select(RecruitmentExperience)
        .where(
            RecruitmentExperience.company_id == company.id,
            RecruitmentExperience.verification_status.in_(PUBLIC_REPORT_STATUSES),
        )
        .order_by(RecruitmentExperience.application_date.desc())
        .limit(limit)
    )
    return [PublicReportCard.model_validate(r) for r in rows.scalars().all()]


@router.get(
    "/{slug}/jobs",
    response_model=Page[JobCard],
    dependencies=[Depends(require_jobs_enabled)],
)
async def jobs(
    slug: str,
    db: DbSession,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[JobCard]:
    """The company jobs tab. Postings say a company is hiring; they say
    nothing about how it answers, so nothing here feeds a metric."""
    company = await service.get_company_by_slug(db, slug)
    page = await jobs_service.list_jobs(db, company_id=company.id, cursor=cursor, limit=limit)
    return Page(
        items=[JobCard.of(row.job, row.company) for row in page.rows],
        next_cursor=page.next_cursor,
    )


@router.post("/request", response_model=CompanyAddRequestAccepted, status_code=202)
async def request_company(
    payload: CompanyAddRequestInput, db: DbSession, user: OptionalUser
) -> CompanyAddRequestAccepted:
    record = await service.create_add_request(
        db,
        name=payload.name,
        website=payload.website,
        industry=payload.industry,
        note=payload.note,
        user_id=user.id if user else None,
    )
    await db.commit()
    return CompanyAddRequestAccepted(id=record.id, status=record.status)
