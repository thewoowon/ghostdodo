from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request

from app.api_deps import ContributingUser, CurrentUser, DbSession, client_ip
from app.core import rate_limit
from app.core.config import settings
from app.core.methodology import get_methodology
from app.core.security import hash_ip
from app.modules.evidence import service as evidence_service
from app.modules.evidence.schemas import (
    EvidenceCompleteInput,
    EvidenceSummary,
    UploadIntentInput,
    UploadIntentOutput,
)
from app.modules.reports import service
from app.modules.reports.schemas import (
    OwnReport,
    QuickLogInput,
    QuickLogResult,
    ReportInput,
    ReportUpdate,
)
from app.modules.reputation import service as reputation_service
from app.shared.enums import ReputationEventType

router = APIRouter(prefix="/reports", tags=["reports"])

IdempotencyKey = Annotated[str | None, Header(alias="X-Idempotency-Key")]


@router.post("", response_model=OwnReport, status_code=201)
async def create_report(
    payload: ReportInput,
    db: DbSession,
    user: ContributingUser,
    idempotency_key: IdempotencyKey = None,
) -> OwnReport:
    report = await service.create_draft(
        db, user_id=user.id, payload=payload, idempotency_key=idempotency_key
    )
    await db.commit()
    return OwnReport.model_validate(report)


@router.post("/batch", response_model=QuickLogResult, status_code=201)
async def submit_quick_log(
    payload: QuickLogInput, db: DbSession, user: ContributingUser
) -> QuickLogResult:
    """Up to 30 companies in one go, counted as one submission against the
    daily limit — the limit is there to slow abuse, not to make someone who
    applied to thirty companies come back on three different days.

    No reputation is awarded here. The wizard awards it for a complete
    record at submission; a quick-log line is deliberately thin, and
    granting standing per line would make thirty lines the cheapest way to
    rank up. Standing arrives when a moderator verifies the line.
    """
    await rate_limit.enforce("report_submit", str(user.id), rate_limit.REPORT_SUBMIT)
    result = await service.submit_quick_log(
        db, user_id=user.id, payload=payload, methodology=get_methodology()
    )
    await db.commit()
    return result


@router.get("/{report_id}", response_model=OwnReport)
async def get_report(report_id: uuid.UUID, db: DbSession, user: CurrentUser) -> OwnReport:
    report = await service.get_own_report(db, report_id=report_id, user_id=user.id)
    return OwnReport.model_validate(report)


@router.patch("/{report_id}", response_model=OwnReport)
async def update_report(
    report_id: uuid.UUID, payload: ReportUpdate, db: DbSession, user: CurrentUser
) -> OwnReport:
    report = await service.update_draft(db, report_id=report_id, user_id=user.id, payload=payload)
    await db.commit()
    return OwnReport.model_validate(report)


@router.post("/{report_id}/submit", response_model=OwnReport)
async def submit_report(
    report_id: uuid.UUID, request: Request, db: DbSession, user: ContributingUser
) -> OwnReport:
    await rate_limit.enforce("report_submit", str(user.id), rate_limit.REPORT_SUBMIT)

    report = await service.submit_report(
        db, report_id=report_id, user_id=user.id, methodology=get_methodology()
    )
    # Submitting a complete structured record is itself worth something —
    # independent of what the record says about the company.
    await reputation_service.award(
        db,
        user=user,
        event_type=ReputationEventType.REPORT_SUBMITTED_COMPLETE,
        subject_type="recruitment_experience",
        subject_id=report.id,
        dedupe_key=f"report_submitted:{report.id}",
    )
    # One transaction: the report and its reputation effect commit together.
    await db.commit()
    return OwnReport.model_validate(report)


@router.post(
    "/{report_id}/evidence/upload-intent",
    response_model=UploadIntentOutput,
    status_code=201,
)
async def create_upload_intent(
    report_id: uuid.UUID,
    payload: UploadIntentInput,
    request: Request,
    db: DbSession,
    user: ContributingUser,
) -> UploadIntentOutput:
    identity = hash_ip(client_ip(request)) or str(user.id)
    await rate_limit.enforce("evidence_upload", identity, rate_limit.EVIDENCE_UPLOAD)

    evidence, presigned = await evidence_service.create_upload_intent(
        db, report_id=report_id, user_id=user.id, payload=payload
    )
    await db.commit()
    fields: dict[str, Any] = dict(presigned["fields"])
    return UploadIntentOutput(
        evidence_id=evidence.id,
        upload_url=str(presigned["url"]),
        fields=fields,
        expires_in_seconds=settings.evidence_upload_url_ttl_seconds,
    )


@router.post("/{report_id}/evidence/{evidence_id}/complete", response_model=EvidenceSummary)
async def complete_evidence(
    report_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: EvidenceCompleteInput,
    db: DbSession,
    user: ContributingUser,
) -> EvidenceSummary:
    evidence = await evidence_service.complete_upload(
        db,
        report_id=report_id,
        evidence_id=evidence_id,
        user_id=user.id,
        sha256=payload.sha256,
    )
    await db.commit()
    return EvidenceSummary.model_validate(evidence)


@router.get("/{report_id}/evidence", response_model=list[EvidenceSummary])
async def list_evidence(
    report_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> list[EvidenceSummary]:
    items = await evidence_service.list_for_report(db, report_id=report_id, user_id=user.id)
    return [EvidenceSummary.model_validate(e) for e in items]


@router.delete("/{report_id}/evidence/{evidence_id}", status_code=204)
async def delete_evidence(
    report_id: uuid.UUID, evidence_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> None:
    await evidence_service.delete_evidence(
        db, report_id=report_id, evidence_id=evidence_id, user_id=user.id
    )
    await db.commit()
