from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.main import app
from app.modules.companies.models import Company
from app.modules.evidence.models import Evidence, EvidenceAccessLog
from app.modules.reports.models import RecruitmentExperience
from app.modules.reputation.models import CreditLedger, ReputationEvent
from app.modules.users.models import MagicLinkToken, User
from app.modules.verification.models import AuditLog, VerificationReview
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select


@pytest.fixture
async def _reset_rate_limits() -> AsyncIterator[None]:
    """Clears rate-limit counters between tests.

    They are per-identity Redis keys, and every test signs in from the same
    loopback address, so without this the fifth test would start failing with
    429s that have nothing to do with what it asserts. Pulled in by `client`
    rather than autouse, so the pure-unit metric tests stay synchronous.
    """
    redis = get_redis()
    keys = [k async for k in redis.scan_iter("rl:*")]
    if keys:
        await redis.delete(*keys)
    yield


@pytest.fixture
async def client(_reset_rate_limits: None) -> AsyncIterator[AsyncClient]:
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture
async def db() -> AsyncIterator[object]:
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def clean_slice() -> AsyncIterator[str]:
    """Isolates the vertical-slice test from seed data by using a company
    slug nothing else touches, and removing its rows afterwards."""
    slug = f"test-co-{uuid.uuid4().hex[:8]}"
    yield slug
    async with SessionLocal() as session:
        company = (
            await session.execute(Company.__table__.select().where(Company.slug == slug))
        ).first()
        if company is not None:
            company_id = company.id
            report_ids = [
                r.id
                for r in (
                    await session.execute(
                        RecruitmentExperience.__table__.select().where(
                            RecruitmentExperience.company_id == company_id
                        )
                    )
                ).all()
            ]
            if report_ids:
                evidence_ids = [
                    e.id
                    for e in (
                        await session.execute(
                            Evidence.__table__.select().where(
                                Evidence.experience_id.in_(report_ids)
                            )
                        )
                    ).all()
                ]
                if evidence_ids:
                    await session.execute(
                        delete(EvidenceAccessLog).where(
                            EvidenceAccessLog.evidence_id.in_(evidence_ids)
                        )
                    )
                    await session.execute(delete(Evidence).where(Evidence.id.in_(evidence_ids)))
                await session.execute(
                    delete(VerificationReview).where(
                        VerificationReview.experience_id.in_(report_ids)
                    )
                )
            await session.execute(
                delete(RecruitmentExperience).where(RecruitmentExperience.company_id == company_id)
            )
            await session.execute(delete(Company).where(Company.id == company_id))
        await session.commit()


async def cleanup_user(email: str) -> None:
    """Removes a test user and everything that references them.

    Order matters: `recruitment_experiences.user_id` and the ledgers are
    RESTRICT, so dependents have to go first — deepest first, user last.
    """
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is not None:
            report_ids = list(
                (
                    await session.execute(
                        select(RecruitmentExperience.id).where(
                            RecruitmentExperience.user_id == user.id
                        )
                    )
                ).scalars()
            )
            if report_ids:
                evidence_ids = list(
                    (
                        await session.execute(
                            select(Evidence.id).where(Evidence.experience_id.in_(report_ids))
                        )
                    ).scalars()
                )
                if evidence_ids:
                    await session.execute(
                        delete(EvidenceAccessLog).where(
                            EvidenceAccessLog.evidence_id.in_(evidence_ids)
                        )
                    )
                    await session.execute(delete(Evidence).where(Evidence.id.in_(evidence_ids)))
                await session.execute(
                    delete(VerificationReview).where(
                        VerificationReview.experience_id.in_(report_ids)
                    )
                )
                await session.execute(
                    delete(RecruitmentExperience).where(RecruitmentExperience.id.in_(report_ids))
                )
            # Reviews and access logs this user performed as a moderator.
            await session.execute(
                delete(VerificationReview).where(VerificationReview.reviewer_id == user.id)
            )
            await session.execute(
                delete(EvidenceAccessLog).where(EvidenceAccessLog.accessed_by_user_id == user.id)
            )
            await session.execute(delete(ReputationEvent).where(ReputationEvent.user_id == user.id))
            await session.execute(delete(CreditLedger).where(CreditLedger.user_id == user.id))
            await session.execute(delete(AuditLog).where(AuditLog.actor_user_id == user.id))
            await session.execute(delete(User).where(User.id == user.id))
        await session.execute(delete(MagicLinkToken).where(MagicLinkToken.email == email))
        await session.commit()
