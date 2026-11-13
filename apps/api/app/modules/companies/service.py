"""Company directory and search."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Float, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.directory import DirectoryRecord, upsert_record
from app.modules.companies.models import Company, CompanyAddRequest
from app.modules.companies.normalize import match_key
from app.modules.verification.models import AuditLog
from app.shared.enums import AuditAction
from app.shared.errors import CompanyNotFoundError, NotFoundError, ValidationError

# Korean company names are written many ways: `(주)도도랩`, `주식회사 도도랩`,
# `도도랩`. Normalizing before matching means a user need not guess the form.
_LEGAL_FORM_PATTERNS = (
    r"\(주\)",
    r"\(유\)",
    r"주식회사",
    r"유한회사",
    r"유한책임회사",
    r"\bInc\.?\b",
    r"\bCorp\.?\b",
    r"\bLtd\.?\b",
    r"\bCo\.?\b",
)
_LEGAL_FORM_RE = re.compile("|".join(_LEGAL_FORM_PATTERNS), re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")

# Below this trigram similarity the results are noise rather than typos.
_SIMILARITY_FLOOR = 0.2


def normalize_company_query(raw: str) -> str:
    without_form = _LEGAL_FORM_RE.sub(" ", raw)
    return _WHITESPACE_RE.sub(" ", without_form).strip()


async def search_companies(session: AsyncSession, *, query: str, limit: int = 20) -> list[Company]:
    """Typo-tolerant search across Korean name, English name, and aliases.

    Ranking combines exact-prefix (what the user almost always means) with
    trigram similarity (what they meant to type), then report volume as the
    tie-breaker.
    """
    normalized = normalize_company_query(query)
    if not normalized:
        return []

    pattern = f"{normalized}%"
    contains = f"%{normalized}%"

    name_similarity = func.greatest(
        func.similarity(Company.display_name_ko, normalized),
        func.similarity(Company.legal_name_ko, normalized),
        func.coalesce(func.similarity(Company.name_en, normalized), 0.0),
    )

    # Aliases live in an array; compare against them as a joined string so one
    # expression covers every stored spelling.
    alias_blob = func.array_to_string(Company.aliases, " ")
    alias_similarity = func.coalesce(func.similarity(alias_blob, normalized), 0.0)

    similarity = func.greatest(name_similarity, alias_similarity)

    prefix_match = func.coalesce(
        Company.display_name_ko.ilike(pattern)
        | Company.legal_name_ko.ilike(pattern)
        | func.coalesce(Company.name_en.ilike(pattern), False)
        | alias_blob.ilike(contains),
        False,
    )

    stmt = (
        select(Company)
        .where(
            or_(
                prefix_match,
                similarity >= _SIMILARITY_FLOOR,
                cast(Company.display_name_ko, String).ilike(contains),
            )
        )
        .order_by(
            prefix_match.desc(),
            cast(similarity, Float).desc(),
            Company.public_report_count.desc(),
            Company.display_name_ko.asc(),
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_company_by_slug(session: AsyncSession, slug: str) -> Company:
    company = (
        await session.execute(select(Company).where(Company.slug == slug))
    ).scalar_one_or_none()
    if company is None:
        raise CompanyNotFoundError()
    return company


async def get_company_by_id(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError()
    return company


@dataclass(frozen=True)
class AddRequestOutcome:
    request: CompanyAddRequest | None
    existing: Company | None


async def create_add_request(
    session: AsyncSession,
    *,
    name: str,
    website: str | None,
    industry: str | None,
    note: str | None,
    user_id: uuid.UUID | None,
) -> AddRequestOutcome:
    """Queued for review rather than inserted directly — the directory is not
    open to anonymous writes.

    Two cases queue nothing. A name that already belongs to a company (a
    spelling the search did not surface) returns that company. A name
    already waiting returns the pending request, so the queue holds one
    entry per company however many people ask.
    """
    key = match_key(name)
    if key:
        existing = (
            await session.execute(select(Company).where(Company.match_key == key))
        ).scalar_one_or_none()
        if existing is not None:
            return AddRequestOutcome(request=None, existing=existing)

        pending = (
            (
                await session.execute(
                    select(CompanyAddRequest).where(CompanyAddRequest.status == "PENDING")
                )
            )
            .scalars()
            .all()
        )
        for row in pending:
            if match_key(row.submitted_name) == key:
                return AddRequestOutcome(request=row, existing=None)

    request = CompanyAddRequest(
        submitted_name=name.strip(),
        website=website,
        industry=industry,
        note=note,
        requested_by_user_id=user_id,
    )
    session.add(request)
    await session.flush()
    return AddRequestOutcome(request=request, existing=None)


async def pending_add_requests(session: AsyncSession, *, limit: int) -> list[CompanyAddRequest]:
    return list(
        (
            await session.execute(
                select(CompanyAddRequest)
                .where(CompanyAddRequest.status == "PENDING")
                .order_by(CompanyAddRequest.created_at)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def decide_add_request(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    decision: str,
    company_slug: str | None,
    note: str | None,
    moderator_id: uuid.UUID,
    http_request_id: str | None,
) -> tuple[CompanyAddRequest, Company | None]:
    """Approve, merge, or reject one request, with its audit entry, in the
    caller's transaction.

    APPROVE goes through the same `upsert_record` the registry imports use,
    so the match key still dedupes and a demo fixture still cannot be taken
    over by a name collision. The company it creates is a real one: held
    back by the launch gate like any import.
    """
    request = await session.get(CompanyAddRequest, request_id)
    if request is None:
        raise NotFoundError("요청을 찾을 수 없습니다.")
    if request.status != "PENDING":
        raise ValidationError("이미 처리된 요청입니다.", code="REQUEST_ALREADY_DECIDED")

    company: Company | None = None
    if decision == "APPROVE":
        record = DirectoryRecord(
            source="REQUEST",
            source_ref=str(request.id),
            legal_name=request.submitted_name,
            industry=request.industry,
            website=request.website,
        )
        outcome = await upsert_record(session, record)
        company = (
            await session.execute(
                select(Company).where(Company.match_key == match_key(request.submitted_name))
            )
        ).scalar_one_or_none()
        if outcome == "skipped" or company is None or company.is_demo:
            raise ValidationError(
                "이 이름으로는 회사를 만들 수 없습니다. 기존 회사로 연결하거나 반려해 주세요.",
                code="REQUEST_NOT_CREATABLE",
            )
        request.status = "APPROVED"
    elif decision == "MERGE":
        if not company_slug:
            raise ValidationError("연결할 회사를 지정해 주세요.", code="MERGE_TARGET_REQUIRED")
        company = await get_company_by_slug(session, company_slug)
        request.status = "MERGED"
    else:
        request.status = "REJECTED"

    request.resolved_company_id = company.id if company else None
    request.resolved_at = datetime.now(UTC)

    session.add(
        AuditLog(
            action=AuditAction.COMPANY_ADD_REQUEST_DECISION,
            actor_user_id=moderator_id,
            subject_type="company_add_request",
            subject_id=request.id,
            request_id=http_request_id,
            payload={
                "decision": decision,
                "submitted_name": request.submitted_name,
                "company_id": str(company.id) if company else None,
                "note": note,
            },
        )
    )
    await session.flush()
    return request, company
