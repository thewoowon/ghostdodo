from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api_deps import CurrentUser, DbSession
from app.modules.companies.models import Company
from app.modules.companies.schemas import CompanySummary
from app.modules.evidence.models import Evidence
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.schemas import MyReport, OwnReport
from app.modules.reputation import badges as badge_rules
from app.modules.reputation.models import CreditLedger, ReputationEvent, UserBadge
from app.modules.users.models import SavedCompany

router = APIRouter(prefix="/me", tags=["me"])


class EarnedBadge(BaseModel):
    """Rendered by the client as-is. The label lives here rather than in the
    web bundle so a new badge does not need a front-end deploy."""

    code: str
    label: str
    description: str


class Profile(BaseModel):
    id: uuid.UUID
    handle: str
    role: str
    rank: str
    reputation_score: int
    credit_balance: int
    verified_contribution_count: int
    trust_state: str
    badges: list[EarnedBadge]
    created_at: str


class LedgerEntry(BaseModel):
    id: uuid.UUID
    event_type: str
    delta: int
    balance_after: int
    created_at: str


@router.get("", response_model=Profile)
async def profile(db: DbSession, user: CurrentUser) -> Profile:
    held = (
        (
            await db.execute(
                select(UserBadge.badge_code).where(
                    UserBadge.user_id == user.id, UserBadge.revoked_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    # Rendered in the canonical order, not award order, so a profile does not
    # reshuffle as badges arrive. Unknown codes are dropped rather than shown
    # as a bare identifier.
    earned = [
        EarnedBadge(code=rule.code, label=rule.label, description=rule.description)
        for rule in badge_rules.labels(list(held))
    ]
    return Profile(
        id=user.id,
        handle=user.handle,
        role=user.role.value,
        rank=user.rank.value,
        reputation_score=user.reputation_score,
        credit_balance=user.credit_balance,
        verified_contribution_count=user.verified_contribution_count,
        trust_state=user.trust_state.value,
        badges=earned,
        created_at=user.created_at.isoformat(),
    )


@router.get("/reports", response_model=list[MyReport])
async def my_reports(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> list[MyReport]:
    evidence_counts = (
        select(Evidence.experience_id, func.count(Evidence.id).label("n"))
        .group_by(Evidence.experience_id)
        .subquery()
    )
    rows = await db.execute(
        select(
            RecruitmentExperience,
            func.coalesce(evidence_counts.c.n, 0),
            Company.slug,
            Company.display_name_ko,
        )
        .join(Company, Company.id == RecruitmentExperience.company_id)
        .outerjoin(evidence_counts, evidence_counts.c.experience_id == RecruitmentExperience.id)
        .where(RecruitmentExperience.user_id == user.id)
        .order_by(RecruitmentExperience.created_at.desc())
        .limit(limit)
    )
    return [
        MyReport.model_validate(
            {
                **OwnReport.model_validate(report).model_dump(),
                "evidence_count": count,
                "company_slug": slug,
                "company_name": name,
            }
        )
        for report, count, slug, name in rows.all()
    ]


@router.get("/reputation", response_model=list[LedgerEntry])
async def my_reputation(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> list[LedgerEntry]:
    rows = await db.execute(
        select(ReputationEvent)
        .where(ReputationEvent.user_id == user.id)
        .order_by(ReputationEvent.created_at.desc())
        .limit(limit)
    )
    return [
        LedgerEntry(
            id=e.id,
            event_type=e.event_type.value,
            delta=e.delta,
            balance_after=e.balance_after,
            created_at=e.created_at.isoformat(),
        )
        for e in rows.scalars().all()
    ]


@router.get("/credits", response_model=list[LedgerEntry])
async def my_credits(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> list[LedgerEntry]:
    rows = await db.execute(
        select(CreditLedger)
        .where(CreditLedger.user_id == user.id)
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
    )
    return [
        LedgerEntry(
            id=e.id,
            event_type=e.event_type.value,
            delta=e.delta,
            balance_after=e.balance_after,
            created_at=e.created_at.isoformat(),
        )
        for e in rows.scalars().all()
    ]


@router.get("/saved-companies", response_model=list[CompanySummary])
async def saved_companies(db: DbSession, user: CurrentUser) -> list[CompanySummary]:
    rows = await db.execute(
        select(Company)
        .join(SavedCompany, SavedCompany.company_id == Company.id)
        .where(SavedCompany.user_id == user.id)
        .order_by(SavedCompany.created_at.desc())
    )
    return [CompanySummary.model_validate(c) for c in rows.scalars().all()]


@router.post("/saved-companies/{company_id}", status_code=204)
async def save_company(company_id: uuid.UUID, db: DbSession, user: CurrentUser) -> None:
    existing = (
        await db.execute(
            select(SavedCompany.id).where(
                SavedCompany.user_id == user.id, SavedCompany.company_id == company_id
            )
        )
    ).first()
    if existing is None:
        db.add(SavedCompany(user_id=user.id, company_id=company_id))
        await db.commit()


@router.delete("/saved-companies/{company_id}", status_code=204)
async def unsave_company(company_id: uuid.UUID, db: DbSession, user: CurrentUser) -> None:
    await db.execute(
        delete(SavedCompany).where(
            SavedCompany.user_id == user.id, SavedCompany.company_id == company_id
        )
    )
    await db.commit()
