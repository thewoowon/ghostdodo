from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.shared.enums import CompanyClaimState, CompanySizeBand
from app.shared.schemas import ORMModel


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
