"""Factual correction requests and their resolution.

The workflow from docs/08 §5, implemented literally:

  1. A company submits a factual challenge.
  2. Moderation reviews the source data.
  3. The record may be corrected, relabeled, or removed.
  4. An audit trail is retained internally.
  5. Material aggregate changes trigger metric recomputation.

Two constraints hold throughout. The reporter's identity is never read,
returned, or logged by anything in this module — a company contests the
record, not the person. And a resolution can change a record but never
delete the history of it: every decision is an audit row, and status changes
go through the same verification path a moderator decision uses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.methodology import get_methodology
from app.modules.company_claims.models import CorrectionRequest
from app.modules.disputes.schemas import (
    DISPUTABLE_FIELDS,
    CorrectionOutcome,
    CorrectionRequestInput,
)
from app.modules.metrics.service import recompute_company
from app.modules.reports.models import RecruitmentExperience
from app.modules.reputation import service as reputation_service
from app.modules.users.models import User
from app.modules.verification.models import AuditLog, VerificationReview
from app.shared.enums import (
    PUBLIC_REPORT_STATUSES,
    AuditAction,
    ReviewDecision,
    VerificationStatus,
)
from app.shared.errors import NotFoundError, ValidationError

log = get_logger(__name__)

# What each resolution does to the contested record's status.
_OUTCOME_STATUS: dict[CorrectionOutcome, VerificationStatus | None] = {
    CorrectionOutcome.UPHELD: None,
    CorrectionOutcome.REJECTED: None,
    CorrectionOutcome.CORRECTED: None,
    CorrectionOutcome.RELABELED: VerificationStatus.PARTIALLY_VERIFIED,
    CorrectionOutcome.REMOVED: VerificationStatus.REMOVED,
}


async def submit(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    payload: CorrectionRequestInput,
    submitted_by_user_id: uuid.UUID | None,
) -> CorrectionRequest:
    if payload.experience_id is not None:
        report = await session.get(RecruitmentExperience, payload.experience_id)
        # A challenge must name a record that is actually on this company's
        # page; otherwise it is a probe for whether some report id exists.
        if report is None or report.company_id != company_id:
            raise NotFoundError("해당 기록을 찾을 수 없습니다.")

    unknown = set(payload.disputed_fields) - DISPUTABLE_FIELDS
    if unknown:
        raise ValidationError(
            "정정을 요청할 수 없는 항목이 포함되어 있습니다.",
            details={"unsupported_fields": sorted(unknown)},
        )

    request = CorrectionRequest(
        company_id=company_id,
        experience_id=payload.experience_id,
        submitted_by_user_id=submitted_by_user_id,
        contact_email=payload.contact_email,
        claim_summary=payload.claim_summary,
        disputed_fields=list(payload.disputed_fields),
        supporting_note=payload.supporting_note,
        status="OPEN",
    )
    session.add(request)
    await session.flush()

    # Contesting a record marks it disputed while review is pending, so the
    # public page can say so rather than presenting it as settled.
    if payload.experience_id is not None:
        report = await session.get(RecruitmentExperience, payload.experience_id)
        if report is not None and report.verification_status in PUBLIC_REPORT_STATUSES:
            report.verification_status = VerificationStatus.DISPUTED
            await recompute_company(session, company_id, methodology=get_methodology())

    session.add(
        AuditLog(
            action=AuditAction.COMPANY_CORRECTION,
            actor_user_id=submitted_by_user_id,
            subject_type="correction_request",
            subject_id=request.id,
            payload={
                "company_id": str(company_id),
                "experience_id": str(payload.experience_id) if payload.experience_id else None,
                "disputed_fields": list(payload.disputed_fields),
            },
        )
    )
    await session.flush()
    log.info("correction.submitted", request_id=str(request.id))
    return request


def _coerce(field: str, raw: str | bool | None) -> Any:
    """Correction values arrive as strings from a form; convert to the column
    type so a moderator cannot write a malformed date into a record."""
    if raw is None:
        return None
    if field in ("promised_result", "result_received"):
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("true", "1", "yes", "y")
    if field in ("application_date", "promised_result_date"):
        return date.fromisoformat(str(raw))
    if field == "result_received_at":
        return datetime.fromisoformat(str(raw))
    return str(raw)


async def decide(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    moderator: User,
    outcome: CorrectionOutcome,
    decision_note: str | None,
    field_corrections: dict[str, str | bool | None],
    http_request_id: str | None = None,
) -> CorrectionRequest:
    """Resolve a challenge. One transaction, like every moderation write."""
    request = await session.get(CorrectionRequest, request_id)
    if request is None:
        raise NotFoundError("정정 요청을 찾을 수 없습니다.")
    if request.status != "OPEN":
        raise ValidationError("이미 처리된 정정 요청입니다.")

    unknown = set(field_corrections) - DISPUTABLE_FIELDS
    if unknown:
        raise ValidationError(
            "정정할 수 없는 항목입니다.", details={"unsupported_fields": sorted(unknown)}
        )
    if outcome is not CorrectionOutcome.CORRECTED and field_corrections:
        raise ValidationError("항목 수정은 CORRECTED 결정에서만 가능합니다.")

    report = (
        await session.get(RecruitmentExperience, request.experience_id)
        if request.experience_id
        else None
    )
    applied: dict[str, str] = {}
    status_before = report.verification_status if report else None

    if report is not None:
        if outcome is CorrectionOutcome.CORRECTED:
            for field, raw in field_corrections.items():
                try:
                    value = _coerce(field, raw)
                except ValueError as exc:
                    raise ValidationError(f"'{field}' 값의 형식이 올바르지 않습니다.") from exc
                applied[field] = f"{getattr(report, field)!r} -> {value!r}"
                setattr(report, field, value)
            # A corrected record returns to the public set; the challenge
            # fixed a fact, it did not disqualify the observation.
            report.verification_status = VerificationStatus.VERIFIED
        elif outcome in (CorrectionOutcome.UPHELD, CorrectionOutcome.REJECTED):
            # The record was disputed on submission; restore it.
            report.verification_status = VerificationStatus.VERIFIED
        else:
            new_status = _OUTCOME_STATUS[outcome]
            if new_status is not None:
                report.verification_status = new_status

        session.add(
            VerificationReview(
                experience_id=report.id,
                reviewer_id=moderator.id,
                decision=(
                    ReviewDecision.REMOVE
                    if outcome is CorrectionOutcome.REMOVED
                    else ReviewDecision.VERIFY
                ),
                status_before=status_before or report.verification_status,
                status_after=report.verification_status,
                reasons=[f"correction:{outcome.value}"],
                structured_checks={"applied_corrections": applied},
                note=decision_note,
            )
        )

    request.status = "RESOLVED"
    request.outcome = outcome.value
    request.decision_note = decision_note
    request.decided_by_user_id = moderator.id
    request.decided_at = datetime.now(UTC)

    session.add(
        AuditLog(
            action=AuditAction.COMPANY_CORRECTION,
            actor_user_id=moderator.id,
            subject_type="correction_request",
            subject_id=request.id,
            request_id=http_request_id,
            payload={
                "outcome": outcome.value,
                "applied_corrections": applied,
                "experience_id": str(request.experience_id) if request.experience_id else None,
            },
        )
    )

    # A removal overturns a contribution, so the ledger records the reversal.
    if report is not None and outcome is CorrectionOutcome.REMOVED:
        author = await session.get(User, report.user_id)
        if author is not None:
            await reputation_service.reverse(
                session,
                user=author,
                original_event_id=report.id,
                reason="correction_removed",
            )

    # Any resolution can move a record in or out of the public set, so the
    # company's aggregates are always recomputed.
    await recompute_company(session, request.company_id, methodology=get_methodology())
    await session.flush()

    log.info("correction.decided", request_id=str(request.id), outcome=outcome.value)
    return request


async def list_open(
    session: AsyncSession, *, status: str = "OPEN", limit: int = 50
) -> list[CorrectionRequest]:
    rows = await session.execute(
        select(CorrectionRequest)
        .where(CorrectionRequest.status == status)
        # Oldest first: a company waiting on a correction should not be stuck
        # behind newer submissions.
        .order_by(CorrectionRequest.created_at.asc())
        .limit(limit)
    )
    return list(rows.scalars().all())
