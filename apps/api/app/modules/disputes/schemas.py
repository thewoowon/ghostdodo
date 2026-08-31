from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field

from app.shared.schemas import ORMModel


class CorrectionOutcome(StrEnum):
    """How a factual challenge was resolved.

    Note what is absent: there is no outcome that discloses who filed the
    report. A correction contests the record, never the reporter (docs/08 §4).
    """

    UPHELD = "UPHELD"
    """Record was accurate; it stands unchanged."""

    CORRECTED = "CORRECTED"
    """A field was factually wrong and has been fixed."""

    RELABELED = "RELABELED"
    """Record was recategorized — e.g. downgraded from verified."""

    REMOVED = "REMOVED"
    """Record failed verification on review and left public aggregates."""

    REJECTED = "REJECTED"
    """The challenge itself did not establish a factual error."""


# Only the fields a company could plausibly contest as matters of fact.
# Absent by design: outcome and free_context, which are the reporter's own
# account rather than something the company can assert on their behalf.
DISPUTABLE_FIELDS = frozenset(
    {
        "application_date",
        "furthest_stage",
        "promised_result",
        "promised_result_date",
        "result_received",
        "result_received_at",
        "role_title",
        "employment_type",
    }
)


class CorrectionRequestInput(BaseModel):
    """A company's factual challenge.

    `experience_id` is optional: a company may contest one record, or raise a
    concern about the page as a whole.
    """

    experience_id: uuid.UUID | None = None
    contact_email: EmailStr
    claim_summary: str = Field(min_length=10, max_length=2000)
    disputed_fields: list[str] = Field(default_factory=list, max_length=10)
    supporting_note: str | None = Field(default=None, max_length=2000)


class CorrectionRequestAccepted(BaseModel):
    id: uuid.UUID
    status: str
    message: str = "정정 요청이 접수되었습니다. 검토 결과는 입력하신 이메일로 안내드립니다."


class CorrectionRequestSummary(ORMModel):
    """Moderator-facing view of a pending challenge."""

    id: uuid.UUID
    company_id: uuid.UUID
    experience_id: uuid.UUID | None
    contact_email: str | None
    claim_summary: str
    disputed_fields: list[str]
    supporting_note: str | None
    status: str
    outcome: str | None
    created_at: datetime
    decided_at: datetime | None


class CorrectionDecisionInput(BaseModel):
    outcome: CorrectionOutcome
    decision_note: str | None = Field(default=None, max_length=2000)
    # Present only for CORRECTED; keys must be in DISPUTABLE_FIELDS.
    field_corrections: dict[str, str | bool | None] = Field(default_factory=dict)


class CompanyStatementInput(BaseModel):
    """A bounded official statement shown on the company page."""

    body: str = Field(min_length=10, max_length=1200)
    publish: bool = True


class CompanyStatementOut(ORMModel):
    id: uuid.UUID
    company_id: uuid.UUID
    body: str
    is_published: bool
    published_at: datetime | None
