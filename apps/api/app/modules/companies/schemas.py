from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.shared.enums import CompanyClaimState, CompanySizeBand
from app.shared.schemas import ORMModel


def publishes(is_demo: bool) -> bool:
    """Whether what a company has been observed doing may be served
    publicly. The single place the launch gate is decided — every public
    company surface asks this, not `is_demo` or the setting directly."""
    return is_demo or settings.publish_real_companies


class CompanySummary(ORMModel):
    """Search results and list cards. Deliberately carries no metrics — a
    card must not imply a rate the sample cannot support."""

    id: uuid.UUID
    slug: str
    display_name_ko: str
    name_en: str | None = None
    industry: str | None = None
    public_report_count: int
    is_demo: bool
    # False while the launch gate holds this company back (see
    # `publishes`). Clients render "공개 준비 중" and nothing observed.
    published: bool = False

    @model_validator(mode="after")
    def _apply_launch_gate(self) -> CompanySummary:
        self.published = publishes(self.is_demo)
        if not self.published:
            # Even a count says how much has been filed about a company.
            self.public_report_count = 0
        return self


class CompanyDetail(CompanySummary):
    legal_name_ko: str
    aliases: list[str]
    website: str | None = None
    size_band: CompanySizeBand
    claim_state: CompanyClaimState


class CompanyAddRequestInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class CompanyAddRequestAccepted(BaseModel):
    id: uuid.UUID
    status: str
    message: str = "등록 요청이 접수되었습니다. 검토 후 도감에 추가됩니다."
