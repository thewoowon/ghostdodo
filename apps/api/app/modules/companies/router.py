from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request
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
)
from app.modules.metrics.schemas import CompanyMetricsOut
from app.modules.metrics.service import get_snapshot
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.schemas import PublicReportCard
from app.shared.enums import PUBLIC_REPORT_STATUSES, MetricWindow

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
    snapshot = await get_snapshot(db, company.id, window)
    methodology = get_methodology()
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
    """Only publicly-visible statuses, and never the reporter."""
    company = await service.get_company_by_slug(db, slug)
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
