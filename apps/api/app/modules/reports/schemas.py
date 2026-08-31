from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.shared.enums import (
    ApplicationSource,
    CommunicationChannel,
    EmploymentType,
    HiringStage,
    Outcome,
    RoleCategory,
    VerificationStatus,
)
from app.shared.schemas import ORMModel

# Free text is short by policy: structured events are the record, prose is
# context (docs/08 §2).
FREE_CONTEXT_MAX = 500


class ReportInput(BaseModel):
    company_id: uuid.UUID
    role_title: str = Field(min_length=1, max_length=120)
    role_category: RoleCategory
    employment_type: EmploymentType
    source: ApplicationSource
    application_date: date
    furthest_stage: HiringStage
    last_company_interaction_at: datetime | None = None

    promised_result: bool = False
    promised_result_date: date | None = None
    promised_window_end_date: date | None = None

    result_received: bool = False
    result_received_at: datetime | None = None
    result_channel: CommunicationChannel | None = None

    outcome: Outcome = Outcome.UNKNOWN
    context_tags: list[str] = Field(default_factory=list, max_length=8)
    free_context: str | None = Field(default=None, max_length=FREE_CONTEXT_MAX)

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> ReportInput:
        if self.promised_result and not (
            self.promised_result_date or self.promised_window_end_date
        ):
            raise ValueError("결과 안내 예정일이 있었다면 날짜를 입력해 주세요.")
        if self.result_received and self.result_received_at is None:
            raise ValueError("결과를 받았다면 받은 날짜를 입력해 주세요.")
        if self.result_received_at and self.result_received_at.date() < self.application_date:
            raise ValueError("결과 수신일이 지원일보다 빠를 수 없습니다.")
        if self.application_date > date.today():
            raise ValueError("지원일이 미래일 수 없습니다.")
        return self


class ReportUpdate(BaseModel):
    """Draft edits only. Every field optional; unset fields stay unchanged."""

    role_title: str | None = Field(default=None, max_length=120)
    role_category: RoleCategory | None = None
    employment_type: EmploymentType | None = None
    source: ApplicationSource | None = None
    application_date: date | None = None
    furthest_stage: HiringStage | None = None
    last_company_interaction_at: datetime | None = None
    promised_result: bool | None = None
    promised_result_date: date | None = None
    promised_window_end_date: date | None = None
    result_received: bool | None = None
    result_received_at: datetime | None = None
    result_channel: CommunicationChannel | None = None
    outcome: Outcome | None = None
    context_tags: list[str] | None = Field(default=None, max_length=8)
    free_context: str | None = Field(default=None, max_length=FREE_CONTEXT_MAX)


class PublicReportCard(ORMModel):
    """What a visitor sees on a company page.

    There is no `user_id` field, and there never should be: reporter identity
    is not exposed to the public or to companies (docs/08 §4).
    """

    id: uuid.UUID
    role_category: RoleCategory
    employment_type: EmploymentType
    furthest_stage: HiringStage
    application_date: date
    promised_result: bool
    promised_result_date: date | None
    result_received: bool
    result_received_at: datetime | None
    outcome: Outcome
    verification_status: VerificationStatus
    context_tags: list[str]
    free_context: str | None
    helpful_count: int


class OwnReport(PublicReportCard):
    """The contributor's own view, which may include draft state."""

    company_id: uuid.UUID
    submitted_at: datetime | None
    created_at: datetime
    evidence_count: int = 0
