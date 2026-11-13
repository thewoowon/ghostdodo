"""Admin console API. Every route here is moderator-gated and audit-logged."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api_deps import DbSession, Moderator
from app.core.config import settings
from app.modules.companies import service as company_service
from app.modules.companies.schemas import (
    CompanyAddRequestDecision,
    CompanyAddRequestItem,
    CompanyAddRequestResolved,
    CompanySummary,
)
from app.modules.evidence import service as evidence_service
from app.modules.evidence.models import Evidence
from app.modules.evidence.schemas import ModeratorEvidenceView
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.schemas import PublicReportCard
from app.modules.verification import service as verification_service
from app.shared.enums import EvidenceReviewState, ReviewDecision, VerificationStatus
from app.shared.errors import NotFoundError

router = APIRouter(prefix="/admin", tags=["admin"])

# The queue a moderator actually works through.
REVIEW_QUEUE_STATUSES = (
    VerificationStatus.NEEDS_REVIEW,
    VerificationStatus.AUTO_CHECKED,
    VerificationStatus.SUBMITTED,
    VerificationStatus.DISPUTED,
)


class QueueItem(PublicReportCard):
    company_id: uuid.UUID
    submitted_at: str | None = None
    auto_check_flags: dict[str, object] = Field(default_factory=dict)
    evidence_count: int = 0


class DecisionInput(BaseModel):
    decision: ReviewDecision
    reasons: list[str] = Field(default_factory=list, max_length=10)
    note: str | None = Field(default=None, max_length=1000)
    structured_checks: dict[str, object] = Field(default_factory=dict)


class EvidenceReviewInput(BaseModel):
    review_state: EvidenceReviewState
    notes: str | None = Field(default=None, max_length=1000)


@router.get("/reports")
async def queue(
    db: DbSession,
    _moderator: Moderator,
    status: Annotated[VerificationStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    statuses = [status] if status else list(REVIEW_QUEUE_STATUSES)
    evidence_counts = (
        select(Evidence.experience_id, func.count(Evidence.id).label("n"))
        .group_by(Evidence.experience_id)
        .subquery()
    )
    rows = await db.execute(
        select(RecruitmentExperience, func.coalesce(evidence_counts.c.n, 0))
        .outerjoin(
            evidence_counts,
            evidence_counts.c.experience_id == RecruitmentExperience.id,
        )
        .where(RecruitmentExperience.verification_status.in_(statuses))
        # Oldest first: nothing should sit in the queue indefinitely.
        .order_by(RecruitmentExperience.submitted_at.asc())
        .limit(limit)
    )
    return [
        {
            **PublicReportCard.model_validate(report).model_dump(mode="json"),
            "company_id": str(report.company_id),
            "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
            "auto_check_flags": report.auto_check_flags,
            "evidence_count": count,
            "batch_id": str(report.batch_id) if report.batch_id else None,
        }
        for report, count in rows.all()
    ]


@router.post("/reports/{report_id}/decision")
async def decide(
    report_id: uuid.UUID,
    payload: DecisionInput,
    request: Request,
    db: DbSession,
    moderator: Moderator,
) -> dict[str, str]:
    report = await verification_service.decide(
        db,
        report_id=report_id,
        reviewer=moderator,
        decision=payload.decision,
        reasons=payload.reasons,
        note=payload.note,
        structured_checks=payload.structured_checks,
        request_id=getattr(request.state, "request_id", None),
    )
    # Review row, status change, audit entry, reputation, and metric
    # recompute all commit together or not at all.
    await db.commit()
    return {"id": str(report.id), "verification_status": report.verification_status.value}


@router.get("/evidence/{evidence_id}", response_model=ModeratorEvidenceView)
async def view_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: DbSession,
    moderator: Moderator,
) -> ModeratorEvidenceView:
    """Issues a short-lived signed URL. The access is logged before the URL
    is minted, not after."""
    evidence, url = await evidence_service.issue_moderator_url(
        db,
        evidence_id=evidence_id,
        moderator=moderator,
        purpose="moderation_review",
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return ModeratorEvidenceView(
        id=evidence.id,
        kind=evidence.kind,
        content_type=evidence.content_type,
        size_bytes=evidence.size_bytes,
        original_filename=evidence.original_filename,
        review_state=evidence.review_state,
        access_state=evidence.access_state,
        created_at=evidence.created_at,
        signed_url=url,
        signed_url_expires_in_seconds=settings.evidence_moderator_url_ttl_seconds,
    )


@router.post("/evidence/{evidence_id}/review", response_model=dict)
async def review_evidence(
    evidence_id: uuid.UUID,
    payload: EvidenceReviewInput,
    db: DbSession,
    moderator: Moderator,
) -> dict[str, str]:
    evidence = await evidence_service.set_review_state(
        db,
        evidence_id=evidence_id,
        moderator=moderator,
        state=payload.review_state,
        notes=payload.notes,
    )
    await db.commit()
    return {"id": str(evidence.id), "review_state": evidence.review_state.value}


@router.get("/company-requests", response_model=list[CompanyAddRequestItem])
async def company_requests(
    db: DbSession,
    _moderator: Moderator,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CompanyAddRequestItem]:
    """Oldest first. Each carries the closest existing companies so a variant
    spelling can be merged rather than created twice."""
    items: list[CompanyAddRequestItem] = []
    for row in await company_service.pending_add_requests(db, limit=limit):
        matches = await company_service.search_companies(db, query=row.submitted_name, limit=3)
        items.append(
            CompanyAddRequestItem(
                id=row.id,
                submitted_name=row.submitted_name,
                website=row.website,
                industry=row.industry,
                note=row.note,
                created_at=row.created_at,
                possible_matches=[CompanySummary.model_validate(c) for c in matches],
            )
        )
    return items


@router.post("/company-requests/{request_id}/decision", response_model=CompanyAddRequestResolved)
async def decide_company_request(
    request_id: uuid.UUID,
    payload: CompanyAddRequestDecision,
    request: Request,
    db: DbSession,
    moderator: Moderator,
) -> CompanyAddRequestResolved:
    record, company = await company_service.decide_add_request(
        db,
        request_id=request_id,
        decision=payload.decision,
        company_slug=payload.company_slug,
        note=payload.note,
        moderator_id=moderator.id,
        http_request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return CompanyAddRequestResolved(
        id=record.id, status=record.status, company_slug=company.slug if company else None
    )


class BatchDecisionInput(BaseModel):
    decision: Literal["PARTIALLY_VERIFY", "REJECT"]
    note: str | None = Field(default=None, max_length=1000)


class BatchDecisionResult(BaseModel):
    decided: int
    # Lines the auto-checks flagged. A batch approval never covers them;
    # they stay in the queue for one-by-one review.
    left_for_review: int


@router.post("/report-batches/{batch_id}/decision", response_model=BatchDecisionResult)
async def decide_batch(
    batch_id: uuid.UUID,
    payload: BatchDecisionInput,
    request: Request,
    db: DbSession,
    moderator: Moderator,
) -> BatchDecisionResult:
    """One decision across a quick log, in one transaction.

    Approval is partial verification, and only for lines that passed the
    auto-checks: a quick-log line carries no evidence, so it cannot be fully
    verified, and a flagged line needs a human to look at it. Each line still
    goes through `verification_service.decide`, so the review row, audit
    entry, reputation, and recompute are exactly those of a single decision.
    """
    rows = (
        (
            await db.execute(
                select(RecruitmentExperience).where(
                    RecruitmentExperience.batch_id == batch_id,
                    RecruitmentExperience.verification_status.in_(REVIEW_QUEUE_STATUSES),
                )
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        raise NotFoundError("검토할 묶음을 찾을 수 없습니다.")

    if payload.decision == "PARTIALLY_VERIFY":
        targets = [r for r in rows if r.verification_status is VerificationStatus.AUTO_CHECKED]
        decision = ReviewDecision.PARTIALLY_VERIFY
    else:
        targets = list(rows)
        decision = ReviewDecision.REJECT

    for report in targets:
        await verification_service.decide(
            db,
            report_id=report.id,
            reviewer=moderator,
            decision=decision,
            reasons=[f"batch:{batch_id}"],
            note=payload.note,
            request_id=getattr(request.state, "request_id", None),
        )
    await db.commit()
    return BatchDecisionResult(decided=len(targets), left_for_review=len(rows) - len(targets))
