from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api_deps import DbSession, Moderator, OptionalUser, client_ip
from app.core import rate_limit
from app.core.security import hash_ip
from app.modules.companies import service as company_service
from app.modules.disputes import service
from app.modules.disputes.schemas import (
    CorrectionDecisionInput,
    CorrectionRequestAccepted,
    CorrectionRequestInput,
    CorrectionRequestSummary,
)

router = APIRouter(tags=["corrections"])

# A correction route is mandatory on every company page (docs/08 §5), so it
# is deliberately open rather than gated behind a verified claim — requiring
# ownership proof first would make the route exist without working.
CORRECTION_SUBMIT = rate_limit.RateLimit(limit=5, window_seconds=60 * 60)


@router.post(
    "/companies/{slug}/corrections",
    response_model=CorrectionRequestAccepted,
    status_code=202,
)
async def submit_correction(
    slug: str,
    payload: CorrectionRequestInput,
    request: Request,
    db: DbSession,
    user: OptionalUser,
) -> CorrectionRequestAccepted:
    identity = hash_ip(client_ip(request)) or "anon"
    await rate_limit.enforce("correction_submit", identity, CORRECTION_SUBMIT)

    company = await company_service.get_company_by_slug(db, slug)
    record = await service.submit(
        db,
        company_id=company.id,
        payload=payload,
        submitted_by_user_id=user.id if user else None,
    )
    await db.commit()
    return CorrectionRequestAccepted(id=record.id, status=record.status)


@router.get("/admin/disputes", response_model=list[CorrectionRequestSummary])
async def list_disputes(
    db: DbSession,
    _moderator: Moderator,
    status: Annotated[str, Query()] = "OPEN",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CorrectionRequestSummary]:
    rows = await service.list_open(db, status=status, limit=limit)
    return [CorrectionRequestSummary.model_validate(r) for r in rows]


@router.post("/admin/disputes/{request_id}/decision")
async def decide_dispute(
    request_id: uuid.UUID,
    payload: CorrectionDecisionInput,
    request: Request,
    db: DbSession,
    moderator: Moderator,
) -> dict[str, str]:
    record = await service.decide(
        db,
        request_id=request_id,
        moderator=moderator,
        outcome=payload.outcome,
        decision_note=payload.decision_note,
        field_corrections=payload.field_corrections,
        http_request_id=getattr(request.state, "request_id", None),
    )
    # Record change, review row, audit entry, reputation, and recompute all
    # commit together.
    await db.commit()
    return {"id": str(record.id), "status": record.status, "outcome": record.outcome or ""}
