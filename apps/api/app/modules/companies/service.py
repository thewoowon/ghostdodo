"""Company directory and search."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import Float, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company, CompanyAddRequest
from app.shared.errors import CompanyNotFoundError

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


async def create_add_request(
    session: AsyncSession,
    *,
    name: str,
    website: str | None,
    industry: str | None,
    note: str | None,
    user_id: uuid.UUID | None,
) -> CompanyAddRequest:
    """Queued for review rather than inserted directly — the directory is not
    open to anonymous writes."""
    request = CompanyAddRequest(
        submitted_name=name.strip(),
        website=website,
        industry=industry,
        note=note,
        requested_by_user_id=user_id,
    )
    session.add(request)
    await session.flush()
    return request
