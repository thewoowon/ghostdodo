"""Moderation decisions and their downstream effects.

A decision is one transaction: review row, status change, audit entry,
reputation ledger, and metric recompute either all land or none do. A
verified report that never reached the company's numbers — or reputation
awarded for a report that was actually rejected — would be worse than a
failed request.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.methodology import get_methodology
from app.modules.evidence.models import Evidence
from app.modules.metrics.service import recompute_company
from app.modules.reports.models import RecruitmentExperience
from app.modules.reputation import service as reputation_service
from app.modules.users.models import User
from app.modules.verification.models import AuditLog, VerificationReview
from app.shared.enums import (
    PUBLIC_REPORT_STATUSES,
    AuditAction,
    EvidenceReviewState,
    ReputationEventType,
    ReviewDecision,
    TrustState,
    VerificationStatus,
)
from app.shared.errors import ReportNotFoundError, ValidationError

log = get_logger(__name__)

DECISION_TO_STATUS: dict[ReviewDecision, VerificationStatus] = {
    ReviewDecision.VERIFY: VerificationStatus.VERIFIED,
    ReviewDecision.PARTIALLY_VERIFY: VerificationStatus.PARTIALLY_VERIFIED,
    ReviewDecision.REJECT: VerificationStatus.REJECTED,
    ReviewDecision.REQUEST_REDACTION: VerificationStatus.REDACTED,
    ReviewDecision.MARK_DISPUTED: VerificationStatus.DISPUTED,
    ReviewDecision.REMOVE: VerificationStatus.REMOVED,
}

_REVIEWABLE = frozenset(
    {
        VerificationStatus.SUBMITTED,
        VerificationStatus.AUTO_CHECKED,
        VerificationStatus.NEEDS_REVIEW,
        VerificationStatus.VERIFIED,
        VerificationStatus.PARTIALLY_VERIFIED,
        VerificationStatus.DISPUTED,
        VerificationStatus.REDACTED,
    }
)


async def decide(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    reviewer: User,
    decision: ReviewDecision,
    reasons: list[str] | None = None,
    note: str | None = None,
    structured_checks: dict[str, object] | None = None,
    request_id: str | None = None,
) -> RecruitmentExperience:
    report = await session.get(RecruitmentExperience, report_id)
    if report is None:
        raise ReportNotFoundError()

    if report.verification_status is VerificationStatus.DRAFT:
        raise ValidationError("제출되지 않은 기록은 검토할 수 없습니다.")
    if report.verification_status not in _REVIEWABLE:
        raise ValidationError("현재 상태에서는 검토 결정을 적용할 수 없습니다.")

    status_before = report.verification_status
    status_after = DECISION_TO_STATUS[decision]
    was_public = status_before in PUBLIC_REPORT_STATUSES
    now_public = status_after in PUBLIC_REPORT_STATUSES

    session.add(
        VerificationReview(
            experience_id=report.id,
            reviewer_id=reviewer.id,
            decision=decision,
            status_before=status_before,
            status_after=status_after,
            reasons=reasons or [],
            structured_checks=structured_checks or {},
            note=note,
        )
    )
    report.verification_status = status_after

    session.add(
        AuditLog(
            action=AuditAction.VERIFICATION_STATUS_CHANGED,
            actor_user_id=reviewer.id,
            subject_type="recruitment_experience",
            subject_id=report.id,
            request_id=request_id,
            payload={
                "decision": decision.value,
                "from": status_before.value,
                "to": status_after.value,
                "reasons": reasons or [],
            },
        )
    )

    author = await session.get(User, report.user_id)
    if author is not None:
        await _apply_reputation(
            session,
            author=author,
            report=report,
            was_public=was_public,
            now_public=now_public,
            decision=decision,
        )

    # Recompute whenever public visibility changed in either direction — a
    # removed report has to leave the numbers as promptly as a new one enters.
    if was_public != now_public:
        await recompute_company(session, report.company_id, methodology=get_methodology())

    await session.flush()
    log.info(
        "verification.decided",
        report_id=str(report.id),
        decision=decision.value,
        status_after=status_after.value,
    )
    return report


async def _apply_reputation(
    session: AsyncSession,
    *,
    author: User,
    report: RecruitmentExperience,
    was_public: bool,
    now_public: bool,
    decision: ReviewDecision,
) -> None:
    if now_public and not was_public:
        author.verified_contribution_count += 1
        await reputation_service.award(
            session,
            user=author,
            event_type=ReputationEventType.REPORT_VERIFIED,
            subject_type="recruitment_experience",
            subject_id=report.id,
            dedupe_key=f"report_verified:{report.id}",
        )
        has_verified_evidence = await _has_clean_evidence(session, report.id)
        if has_verified_evidence:
            await reputation_service.award(
                session,
                user=author,
                event_type=ReputationEventType.EVIDENCE_VERIFIED,
                subject_type="recruitment_experience",
                subject_id=report.id,
                dedupe_key=f"evidence_verified:{report.id}",
            )
        return

    if was_public and not now_public:
        # An overturned contribution costs standing, and the ledger keeps the
        # pairing so the deduction is explainable.
        await reputation_service.reverse(
            session,
            user=author,
            original_event_id=report.id,
            reason=decision.value,
        )
        if decision is ReviewDecision.REMOVE:
            author.trust_state = TrustState.RESTRICTED


async def _has_clean_evidence(session: AsyncSession, report_id: uuid.UUID) -> bool:
    found = (
        await session.execute(
            select(Evidence.id).where(
                Evidence.experience_id == report_id,
                Evidence.review_state == EvidenceReviewState.CLEAN,
            )
        )
    ).first()
    return found is not None


async def record_audit(
    session: AsyncSession,
    *,
    action: AuditAction,
    actor_user_id: uuid.UUID | None,
    subject_type: str,
    subject_id: uuid.UUID | None,
    payload: dict[str, object] | None = None,
    request_id: str | None = None,
) -> None:
    session.add(
        AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload or {},
            request_id=request_id,
        )
    )


def utcnow() -> datetime:
    return datetime.now(UTC)
