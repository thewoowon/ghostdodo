"""Evidence lifecycle: intent → direct upload → completion → moderation."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.evidence import storage
from app.modules.evidence.models import Evidence, EvidenceAccessLog
from app.modules.evidence.schemas import (
    ALLOWED_CONTENT_TYPES,
    UploadIntentInput,
    extension_for,
)
from app.modules.reports.models import RecruitmentExperience
from app.modules.users.models import User
from app.modules.verification.models import AuditLog
from app.shared.enums import (
    AuditAction,
    EvidenceAccessState,
    EvidenceReviewState,
    VerificationStatus,
)
from app.shared.errors import (
    EvidenceTooLargeError,
    ForbiddenError,
    NotFoundError,
    ReportNotFoundError,
    UnsupportedEvidenceTypeError,
    ValidationError,
)

log = get_logger(__name__)


async def create_upload_intent(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UploadIntentInput,
) -> tuple[Evidence, Mapping[str, Any]]:
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedEvidenceTypeError(details={"allowed": sorted(ALLOWED_CONTENT_TYPES)})
    if payload.size_bytes > settings.evidence_max_bytes:
        raise EvidenceTooLargeError(details={"max_bytes": settings.evidence_max_bytes})

    report = await session.get(RecruitmentExperience, report_id)
    if report is None or report.user_id != user_id:
        raise ReportNotFoundError()
    if report.verification_status not in (
        VerificationStatus.DRAFT,
        VerificationStatus.NEEDS_REVIEW,
    ):
        raise ValidationError("현재 상태의 기록에는 자료를 추가할 수 없습니다.")

    evidence_id = uuid.uuid4()
    object_key = storage.build_object_key(
        report_id, evidence_id, extension_for(payload.content_type)
    )
    evidence = Evidence(
        id=evidence_id,
        experience_id=report_id,
        object_key=object_key,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        original_filename=payload.original_filename,
        kind=payload.kind,
        review_state=EvidenceReviewState.PENDING,
        access_state=EvidenceAccessState.UPLOAD_PENDING,
    )
    session.add(evidence)
    await session.flush()

    presigned = await storage.create_upload_url(
        object_key,
        content_type=payload.content_type,
        max_bytes=settings.evidence_max_bytes,
    )
    return evidence, presigned


async def complete_upload(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    evidence_id: uuid.UUID,
    user_id: uuid.UUID,
    sha256: str | None,
) -> Evidence:
    """Confirms the object exists and records its true size and type as
    reported by storage, not by the client."""
    evidence = await _get_owned(
        session, report_id=report_id, evidence_id=evidence_id, user_id=user_id
    )

    head = await storage.head_object(evidence.object_key)
    if head is None:
        raise ValidationError("업로드가 확인되지 않았습니다. 다시 시도해 주세요.")

    actual_size = int(head.get("ContentLength", 0))
    if actual_size > settings.evidence_max_bytes:
        await storage.delete_object(evidence.object_key)
        evidence.access_state = EvidenceAccessState.DELETED
        await session.flush()
        raise EvidenceTooLargeError(details={"max_bytes": settings.evidence_max_bytes})

    evidence.size_bytes = actual_size
    evidence.sha256 = sha256
    evidence.completed_at = datetime.now(UTC)
    evidence.access_state = EvidenceAccessState.AVAILABLE
    # Stays PENDING until a moderator looks: uploaded is not the same as
    # cleared, and PII review happens before anything counts.
    evidence.review_state = EvidenceReviewState.PENDING
    await session.flush()
    return evidence


async def list_for_report(
    session: AsyncSession, *, report_id: uuid.UUID, user_id: uuid.UUID
) -> list[Evidence]:
    report = await session.get(RecruitmentExperience, report_id)
    if report is None or report.user_id != user_id:
        raise ReportNotFoundError()
    rows = await session.execute(
        select(Evidence).where(
            Evidence.experience_id == report_id,
            Evidence.access_state != EvidenceAccessState.DELETED,
        )
    )
    return list(rows.scalars().all())


async def delete_evidence(
    session: AsyncSession, *, report_id: uuid.UUID, evidence_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    evidence = await _get_owned(
        session, report_id=report_id, evidence_id=evidence_id, user_id=user_id
    )
    await storage.delete_object(evidence.object_key)
    evidence.access_state = EvidenceAccessState.DELETED
    evidence.deleted_at = datetime.now(UTC)
    session.add(
        AuditLog(
            action=AuditAction.EVIDENCE_DELETED,
            actor_user_id=user_id,
            subject_type="evidence",
            subject_id=evidence.id,
            payload={"by": "owner"},
        )
    )
    await session.flush()


async def issue_moderator_url(
    session: AsyncSession,
    *,
    evidence_id: uuid.UUID,
    moderator: User,
    purpose: str,
    request_id: str | None = None,
) -> tuple[Evidence, str]:
    """Mints a short-lived read URL and logs the access before returning it.

    The log entry is written first: if the request fails after this point we
    would rather have an access record with no view than a view with no
    record.
    """
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.access_state is EvidenceAccessState.DELETED:
        raise NotFoundError("자료를 찾을 수 없습니다.")

    session.add(
        EvidenceAccessLog(
            evidence_id=evidence.id,
            accessed_by_user_id=moderator.id,
            purpose=purpose,
            request_id=request_id,
        )
    )
    session.add(
        AuditLog(
            action=AuditAction.EVIDENCE_ACCESSED,
            actor_user_id=moderator.id,
            subject_type="evidence",
            subject_id=evidence.id,
            request_id=request_id,
            payload={"purpose": purpose},
        )
    )
    await session.flush()

    url = await storage.create_moderator_read_url(evidence.object_key)
    log.info("evidence.accessed", evidence_id=str(evidence.id), moderator=str(moderator.id))
    return evidence, url


async def set_review_state(
    session: AsyncSession,
    *,
    evidence_id: uuid.UUID,
    moderator: User,
    state: EvidenceReviewState,
    notes: str | None = None,
) -> Evidence:
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError("자료를 찾을 수 없습니다.")
    evidence.review_state = state
    evidence.pii_notes = notes
    if state in (EvidenceReviewState.REJECTED, EvidenceReviewState.REDACTED):
        evidence.access_state = EvidenceAccessState.QUARANTINED
    session.add(
        AuditLog(
            action=AuditAction.MODERATION_DECISION,
            actor_user_id=moderator.id,
            subject_type="evidence",
            subject_id=evidence.id,
            payload={"review_state": state.value},
        )
    )
    await session.flush()
    return evidence


async def _get_owned(
    session: AsyncSession, *, report_id: uuid.UUID, evidence_id: uuid.UUID, user_id: uuid.UUID
) -> Evidence:
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.experience_id != report_id:
        raise NotFoundError("자료를 찾을 수 없습니다.")
    report = await session.get(RecruitmentExperience, report_id)
    if report is None or report.user_id != user_id:
        raise ForbiddenError()
    return evidence
