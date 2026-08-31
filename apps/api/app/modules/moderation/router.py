"""Admin console API. Every route here is moderator-gated and audit-logged."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api_deps import DbSession, Moderator
from app.core.config import settings
from app.modules.evidence import service as evidence_service
from app.modules.evidence.models import Evidence
from app.modules.evidence.schemas import ModeratorEvidenceView
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.schemas import PublicReportCard
from app.modules.verification import service as verification_service
from app.shared.enums import EvidenceReviewState, ReviewDecision, VerificationStatus

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
