"""Development fixtures.

Hard rule from the handoff: never invent negative records about a real
Korean company. Every company here is fictional, every row is flagged
`is_demo=True`, and the API exposes that flag so the UI can label the data
as sample content.

Usage:  uv run python -m app.scripts.seed [--reset]
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.methodology import get_methodology
from app.db.session import db_session, dispose_engine
from app.modules.companies.models import Company
from app.modules.metrics.service import recompute_company
from app.modules.reports.models import RecruitmentExperience
from app.modules.reports.service import compute_dedupe_hash
from app.modules.users.models import User
from app.shared.enums import (
    ApplicationSource,
    CommunicationChannel,
    CompanySizeBand,
    EmploymentType,
    HiringStage,
    Outcome,
    RoleCategory,
    TrustState,
    UserRole,
    VerificationStatus,
)

# Fictional companies only. The names are deliberately absurd so no reader
# could mistake them for a real employer.
DEMO_COMPANIES: list[dict[str, Any]] = [
    {
        "slug": "dodolab",
        "legal_name_ko": "주식회사 도도랩",
        "display_name_ko": "도도랩",
        "name_en": "DodoLab",
        "aliases": ["도도랩", "dodolab", "(주)도도랩"],
        "industry": "소프트웨어",
        "size_band": CompanySizeBand.B50_199,
        # A company that answers: response rate should come out high.
        "profile": "responsive",
    },
    {
        "slug": "cheolsae-tech",
        "legal_name_ko": "철새테크 주식회사",
        "display_name_ko": "철새테크",
        "name_en": "Cheolsae Tech",
        "aliases": ["철새테크", "cheolsae", "철새 테크"],
        "industry": "IT서비스",
        "size_band": CompanySizeBand.B200_999,
        "profile": "mixed",
    },
    {
        "slug": "hwaseok-soft",
        "legal_name_ko": "화석소프트 주식회사",
        "display_name_ko": "화석소프트",
        "name_en": "Hwaseok Soft",
        "aliases": ["화석소프트", "hwaseoksoft", "화석 소프트"],
        "industry": "소프트웨어",
        "size_band": CompanySizeBand.B10_49,
        "profile": "silent",
    },
    {
        "slug": "nalgae-corp",
        "legal_name_ko": "주식회사 날개코퍼레이션",
        "display_name_ko": "날개코퍼레이션",
        "name_en": "Nalgae Corp",
        "aliases": ["날개코프", "nalgae", "날개"],
        "industry": "커머스",
        "size_band": CompanySizeBand.B1000_PLUS,
        "profile": "promises_broken",
    },
    {
        "slug": "alkkag-studio",
        "legal_name_ko": "알깍스튜디오",
        "display_name_ko": "알깍스튜디오",
        "name_en": "Alkkag Studio",
        "aliases": ["알깍", "alkkag"],
        "industry": "게임",
        "size_band": CompanySizeBand.B10_49,
        # Deliberately under the publishable bar, to exercise `표본 부족`.
        "profile": "sparse",
    },
]


@dataclass(frozen=True, slots=True)
class ProfileShape:
    """How a fictional company behaves, so each demo page exercises a
    different metric state."""

    n: int
    respond_ratio: float
    response_days: tuple[int, int]
    """Inclusive (min, max) days to a disposition when one arrives."""

    promise_ratio: float
    promise_kept: float


_PROFILE_SHAPES: dict[str, ProfileShape] = {
    # Comfortably publishable, and answers nearly everyone.
    "responsive": ProfileShape(34, 0.91, (3, 9), 0.6, 0.9),
    "mixed": ProfileShape(26, 0.62, (7, 21), 0.4, 0.6),
    "silent": ProfileShape(22, 0.27, (14, 35), 0.3, 0.3),
    # Answers about half the time, but usually misses its own stated date.
    "promises_broken": ProfileShape(30, 0.55, (20, 45), 0.8, 0.25),
    # Under the publishable bar on purpose, to exercise `표본 부족`.
    "sparse": ProfileShape(3, 0.5, (5, 12), 0.3, 0.5),
}

STAGES = [
    HiringStage.APPLICATION,
    HiringStage.DOCUMENT_SCREENING,
    HiringStage.TEST,
    HiringStage.ASSIGNMENT,
    HiringStage.INTERVIEW_1,
    HiringStage.INTERVIEW_2_PLUS,
    HiringStage.FINAL_INTERVIEW,
]

ROLE_TITLES = [
    ("프론트엔드 개발자", RoleCategory.SOFTWARE_ENGINEERING),
    ("백엔드 개발자", RoleCategory.SOFTWARE_ENGINEERING),
    ("데이터 분석가", RoleCategory.DATA),
    ("프로덕트 디자이너", RoleCategory.DESIGN),
    ("프로덕트 매니저", RoleCategory.PRODUCT),
    ("퍼포먼스 마케터", RoleCategory.MARKETING),
]


async def seed(reset: bool = False) -> None:
    rng = random.Random(20260901)  # noqa: S311 - fixtures, not security
    now = datetime.now(UTC)

    async with db_session() as session:
        if reset:
            await session.execute(delete(RecruitmentExperience))
            await session.execute(delete(Company).where(Company.is_demo.is_(True)))
            await session.commit()

        # Demo contributors. Emails use the reserved example.com domain so a
        # stray email job can never reach a real inbox.
        contributors: list[User] = []
        for i in range(12):
            email = f"demo{i}@example.com"
            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    handle=f"관찰자{i:02d}",
                    role=UserRole.USER,
                    trust_state=TrustState.ACTIVE,
                    email_verified_at=now,
                )
                session.add(user)
            contributors.append(user)

        moderator_email = "moderator@example.com"
        moderator = (
            await session.execute(select(User).where(User.email == moderator_email))
        ).scalar_one_or_none()
        if moderator is None:
            moderator = User(
                email=moderator_email,
                handle="도도레인저",
                role=UserRole.MODERATOR,
                trust_state=TrustState.ACTIVE,
                email_verified_at=now,
            )
            session.add(moderator)
        await session.flush()

        created: list[Company] = []
        for spec in DEMO_COMPANIES:
            fields = {k: v for k, v in spec.items() if k != "profile"}
            profile = str(spec["profile"])
            company = (
                await session.execute(select(Company).where(Company.slug == spec["slug"]))
            ).scalar_one_or_none()
            if company is None:
                company = Company(is_demo=True, **fields)
                session.add(company)
                await session.flush()
            created.append(company)

            shape = _PROFILE_SHAPES[profile]
            await _seed_reports(
                session,
                company=company,
                contributors=contributors,
                shape=shape,
                rng=rng,
                now=now,
            )

        await session.commit()

        for company in created:
            await recompute_company(session, company.id, methodology=get_methodology(), now=now)
        await session.commit()

        print(f"seeded {len(created)} demo companies")
        for company in created:
            n = (
                (
                    await session.execute(
                        select(RecruitmentExperience).where(
                            RecruitmentExperience.company_id == company.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            print(f"  {company.display_name_ko:12} reports={len(n):3}  (demo)")

    await dispose_engine()


async def _seed_reports(
    session: AsyncSession,
    *,
    company: Company,
    contributors: list[User],
    shape: ProfileShape,
    rng: random.Random,
    now: datetime,
) -> None:
    existing = (
        await session.execute(
            select(RecruitmentExperience.id).where(RecruitmentExperience.company_id == company.id)
        )
    ).first()
    if existing is not None:
        return

    total = shape.n
    respond_ratio = shape.respond_ratio
    lo, hi = shape.response_days
    promise_ratio = shape.promise_ratio
    promise_kept = shape.promise_kept

    for i in range(total):
        user = contributors[i % len(contributors)]
        stage = rng.choice(STAGES)
        title, category = rng.choice(ROLE_TITLES)

        # Spread applications across the last ~10 months so the 6m and 12m
        # windows differ meaningfully.
        applied_days_ago = rng.randint(40, 300)
        application_date = (now - timedelta(days=applied_days_ago)).date()
        last_interaction = now - timedelta(days=applied_days_ago - rng.randint(3, 20))

        responded = rng.random() < respond_ratio
        promised = rng.random() < promise_ratio
        promised_date = (
            (last_interaction + timedelta(days=rng.randint(5, 14))).date() if promised else None
        )

        result_at = None
        outcome = Outcome.UNKNOWN
        if responded:
            delay = rng.randint(lo, hi)
            if promised and rng.random() > promise_kept:
                delay += rng.randint(10, 30)  # answered, but late
            result_at = last_interaction + timedelta(days=delay)
            if result_at > now:
                result_at = now - timedelta(days=1)
            # Most dispositions are rejections; that still counts as a response.
            outcome = Outcome.REJECTED if rng.random() < 0.85 else Outcome.PASSED

        report = RecruitmentExperience(
            id=uuid.uuid4(),
            user_id=user.id,
            company_id=company.id,
            role_title=title,
            role_category=category,
            employment_type=EmploymentType.FULL_TIME,
            source=rng.choice(
                [
                    ApplicationSource.WANTED,
                    ApplicationSource.SARAMIN,
                    ApplicationSource.JOBKOREA,
                    ApplicationSource.COMPANY_SITE,
                    ApplicationSource.JUMPIT,
                ]
            ),
            application_date=application_date,
            furthest_stage=stage,
            last_company_interaction_at=last_interaction,
            promised_result=promised,
            promised_result_date=promised_date,
            result_received=responded,
            result_received_at=result_at,
            result_channel=CommunicationChannel.EMAIL if responded else None,
            outcome=outcome,
            context_tags=[],
            free_context=None,
            verification_status=VerificationStatus.VERIFIED,
            submitted_at=last_interaction + timedelta(days=1),
            methodology_version=get_methodology().version,
            # Fixtures deliberately reuse contributors across many rows, so
            # the fixture index is folded into the hash to keep it unique and
            # within the column's 64-char width.
            dedupe_hash=hashlib.sha256(
                f"{compute_dedupe_hash(user.id, company.id, stage, application_date)}:{i}".encode()
            ).hexdigest(),
        )
        session.add(report)

    company.public_report_count = total
    await session.flush()


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
