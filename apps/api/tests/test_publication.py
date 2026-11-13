"""The launch gate for real companies (docs/08 §11).

Real companies are imported so applicants can report on where they actually
applied, but until Korean legal review closes, nothing a real company has
been observed doing may be served publicly. That is stricter than the sample
bar: a verified report card is public the moment it is verified, with no n
in between, so the gate has to cover cards and counts as well as rates.

The company here has well over the publishable sample, verified, with a
fresh snapshot — everything that would normally publish. With the switch off
none of it may reach a public response.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.core.methodology import get_methodology
from app.db.session import SessionLocal
from app.modules.companies.models import Company
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.metrics.service import recompute_company
from app.modules.reports.models import RecruitmentExperience
from app.modules.users.models import User
from app.shared.enums import (
    ApplicationSource,
    CommunicationChannel,
    EmploymentType,
    HiringStage,
    Outcome,
    RoleCategory,
    TrustState,
    UserRole,
    VerificationStatus,
)
from httpx import AsyncClient
from sqlalchemy import delete

N_REPORTS = 20  # above the 15-report publication bar


async def _company_with_record(*, is_demo: bool) -> tuple[str, list[uuid.UUID]]:
    """A company carrying N verified reports and a recomputed snapshot."""
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        user = User(
            email=f"gate-{tag}@example.com",
            handle=f"게이트{tag}",
            role=UserRole.USER,
            trust_state=TrustState.ACTIVE,
            email_verified_at=now,
        )
        company = Company(
            slug=f"gate-{tag}",
            legal_name_ko=f"주식회사 공개대기{tag}",
            display_name_ko=f"공개대기{tag}",
            aliases=[f"공개대기{tag}"],
            is_demo=is_demo,
        )
        session.add_all([user, company])
        await session.flush()
        for i in range(N_REPORTS):
            interaction = now - timedelta(days=60 + i)
            session.add(
                RecruitmentExperience(
                    user_id=user.id,
                    company_id=company.id,
                    role_title="백엔드 개발자",
                    role_category=RoleCategory.SOFTWARE_ENGINEERING,
                    employment_type=EmploymentType.FULL_TIME,
                    source=ApplicationSource.COMPANY_SITE,
                    application_date=(interaction - timedelta(days=10)).date(),
                    furthest_stage=HiringStage.APPLICATION,
                    last_company_interaction_at=interaction,
                    promised_result=False,
                    result_received=i % 2 == 0,
                    result_received_at=interaction + timedelta(days=5) if i % 2 == 0 else None,
                    result_channel=CommunicationChannel.EMAIL if i % 2 == 0 else None,
                    outcome=Outcome.REJECTED if i % 2 == 0 else Outcome.UNKNOWN,
                    context_tags=[],
                    verification_status=VerificationStatus.VERIFIED,
                    submitted_at=interaction + timedelta(days=1),
                    methodology_version=get_methodology().version,
                    dedupe_hash=hashlib.sha256(f"{tag}:{i}".encode()).hexdigest(),
                )
            )
        company.public_report_count = N_REPORTS
        await session.flush()
        await recompute_company(session, company.id, methodology=get_methodology(), now=now)
        await session.commit()
        return company.slug, [company.id, user.id]


async def _remove(company_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        await session.execute(
            delete(CompanyMetricSnapshot).where(CompanyMetricSnapshot.company_id == company_id)
        )
        await session.execute(
            delete(RecruitmentExperience).where(RecruitmentExperience.company_id == company_id)
        )
        await session.execute(delete(Company).where(Company.id == company_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture
async def real_company(client: AsyncClient) -> AsyncIterator[str]:
    slug, (company_id, user_id) = await _company_with_record(is_demo=False)
    yield slug
    await _remove(company_id, user_id)


@pytest.fixture
async def demo_company(client: AsyncClient) -> AsyncIterator[str]:
    slug, (company_id, user_id) = await _company_with_record(is_demo=True)
    yield slug
    await _remove(company_id, user_id)


class TestRealCompaniesAreHeldBack:
    """Switch off: the company exists and is findable, so applicants can
    report on it — and nothing it has been observed doing is served."""

    @pytest.fixture(autouse=True)
    def _gate_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "publish_real_companies", False)

    async def test_it_exists_but_says_it_is_unpublished(
        self, client: AsyncClient, real_company: str
    ) -> None:
        detail = (await client.get(f"/api/v1/companies/{real_company}")).json()
        assert detail["published"] is False
        # Even a count says how much has been filed about a company.
        assert detail["public_report_count"] == 0

    async def test_search_finds_it_without_a_count(
        self, client: AsyncClient, real_company: str
    ) -> None:
        name = real_company.replace("gate-", "공개대기")
        rows = (await client.get("/api/v1/companies/search", params={"q": name})).json()
        row = next(r for r in rows if r["slug"] == real_company)
        assert row["published"] is False
        assert row["public_report_count"] == 0

    async def test_metrics_are_withheld_not_zero(
        self, client: AsyncClient, real_company: str
    ) -> None:
        metrics = (await client.get(f"/api/v1/companies/{real_company}/metrics")).json()
        assert metrics["withheld"] is True
        assert metrics["qualified_n"] == 0
        assert metrics["stage_breakdown"] == []
        for rate in ("response_rate", "ghost_rate", "broken_promise_rate"):
            assert metrics[rate] is None
        assert metrics["median_response_days"] is None

    async def test_no_report_card_is_served(self, client: AsyncClient, real_company: str) -> None:
        """The case the sample bar never covered: one verified card is
        public the moment it is verified."""
        cards = (await client.get(f"/api/v1/companies/{real_company}/reports")).json()
        assert cards == []

    async def test_demo_fixtures_still_publish(
        self, client: AsyncClient, demo_company: str
    ) -> None:
        detail = (await client.get(f"/api/v1/companies/{demo_company}")).json()
        metrics = (await client.get(f"/api/v1/companies/{demo_company}/metrics")).json()
        cards = (await client.get(f"/api/v1/companies/{demo_company}/reports")).json()
        assert detail["published"] is True
        assert detail["public_report_count"] == N_REPORTS
        assert metrics["withheld"] is False
        assert metrics["qualified_n"] == N_REPORTS
        assert len(cards) == N_REPORTS


class TestOpeningTheGate:
    async def test_the_same_record_publishes_once_switched_on(
        self, client: AsyncClient, real_company: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing is lost while held back: reports were collected and
        aggregated all along, so flipping the switch is the whole launch."""
        monkeypatch.setattr(settings, "publish_real_companies", True)
        detail = (await client.get(f"/api/v1/companies/{real_company}")).json()
        metrics = (await client.get(f"/api/v1/companies/{real_company}/metrics")).json()
        cards = (await client.get(f"/api/v1/companies/{real_company}/reports")).json()
        assert detail["published"] is True
        assert metrics["withheld"] is False
        assert metrics["qualified_n"] == N_REPORTS
        assert metrics["response_rate"] is not None
        assert len(cards) == N_REPORTS
