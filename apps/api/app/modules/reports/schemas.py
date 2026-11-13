from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

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


class MyReport(OwnReport):
    """One row of `/me/reports`.

    The contributor's own list names the company: without it, a list of
    "개발 · 정규직" cards cannot tell one application from another. This is
    the reporter seeing their own record, so naming the company here exposes
    nothing about who reported what to anyone else.
    """

    company_slug: str
    company_name: str


# ── Quick log ────────────────────────────────────────────────────────────
# One applicant has usually applied to dozens of companies. The quick log
# takes what is shared once and one short line per company, and files each
# line as an ordinary report through the same draft-and-submit path.

QUICK_LOG_MAX_ITEMS = 30


class QuickLogDefaults(BaseModel):
    role_title: str = Field(min_length=1, max_length=120)
    role_category: RoleCategory
    employment_type: EmploymentType
    source: ApplicationSource


class QuickLogItem(BaseModel):
    company_id: uuid.UUID
    application_date: date
    furthest_stage: HiringStage
    last_company_interaction_on: date | None = None
    result_received: bool = False
    result_received_on: date | None = None
    outcome: Outcome = Outcome.UNKNOWN

    @model_validator(mode="after")
    def _honest_timing(self) -> QuickLogItem:
        # Without a last contact date the silence clock starts at the
        # application. For anyone who got past it — an interview last week
        # after applying two months ago — that would read as two months of
        # silence. The wizard asks; the quick log must too.
        if (
            self.furthest_stage is not HiringStage.APPLICATION
            and self.last_company_interaction_on is None
        ):
            raise ValueError("지원 이후 단계까지 갔다면 마지막으로 연락받은 날짜가 필요합니다.")
        if self.result_received and self.result_received_on is None:
            raise ValueError("결과를 받은 날짜를 입력해 주세요.")
        return self


class QuickLogInput(BaseModel):
    defaults: QuickLogDefaults
    items: list[QuickLogItem] = Field(min_length=1, max_length=QUICK_LOG_MAX_ITEMS)


class QuickLogItemResult(BaseModel):
    index: int
    company_id: uuid.UUID
    status: Literal["SUBMITTED", "DUPLICATE", "LIMIT", "INVALID"]
    report_id: uuid.UUID | None = None
    message: str | None = None


class QuickLogResult(BaseModel):
    batch_id: uuid.UUID
    submitted: int
    results: list[QuickLogItemResult]
