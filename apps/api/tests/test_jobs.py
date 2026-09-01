"""Linked postings and the outbound apply deep link.

Three things carry weight here and each is asserted directly:

* a posting is a link out, never an observation — seeding one must not move
  a metric (the same rule the directory importer lives under);
* an expired posting leaves the listing but still resolves by id, so a
  shared link explains itself;
* a click is counted as an aggregate, storing a salted visitor hash and a
  same-site path — never a raw IP, never a foreign referrer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.core.config import settings
from app.core.security import hash_ip
from app.db.session import SessionLocal
from app.modules.companies.models import Company
from app.modules.jobs import service
from app.modules.jobs.models import JobPosting, OutboundClick
from app.modules.jobs.schemas import JobCard, is_open, safe_apply_url
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.reports.models import RecruitmentExperience
from app.shared.enums import ApplicationSource, EmploymentType, RoleCategory
from httpx import AsyncClient
from sqlalchemy import delete, func, select

TODAY = date(2026, 8, 31)


def _posting(**overrides: object) -> JobPosting:
    fields: dict[str, object] = {
        "title": "프론트엔드 개발자",
        "role_category": RoleCategory.SOFTWARE_ENGINEERING,
        "employment_type": EmploymentType.FULL_TIME,
        "location": "서울 강남구",
        "source": ApplicationSource.WANTED,
        "source_label": "원티드",
        "source_url": "https://example.com/jobs/1",
        "is_active": True,
        "closes_on": None,
    }
    fields.update(overrides)
    return JobPosting(**fields)  # type: ignore[arg-type]


class TestApplyUrlSafety:
    """A posting URL reaches an `href` as data. Only http(s) may get there."""

    @pytest.mark.parametrize(
        "raw",
        [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "/relative/path",
            "not a url at all",
            "https://",
        ],
    )
    def test_unlinkable_urls_are_dropped(self, raw: str) -> None:
        assert safe_apply_url(raw) is None

    def test_http_and_https_survive(self) -> None:
        assert safe_apply_url("https://example.com/jobs/1") == "https://example.com/jobs/1"
        assert safe_apply_url("  http://example.com/a  ") == "http://example.com/a"


class TestExpiry:
    """Open/closed is derived from the stored dates, so a posting closes on
    schedule without a sweeper having to run."""

    def test_open_without_a_closing_date(self) -> None:
        assert is_open(_posting(), today=TODAY) is True

    def test_open_on_the_closing_date_itself(self) -> None:
        assert is_open(_posting(closes_on=TODAY), today=TODAY) is True

    def test_closed_the_day_after(self) -> None:
        assert is_open(_posting(closes_on=TODAY - timedelta(days=1)), today=TODAY) is False

    def test_deactivated_beats_a_future_closing_date(self) -> None:
        posting = _posting(is_active=False, closes_on=TODAY + timedelta(days=30))
        assert is_open(posting, today=TODAY) is False


class TestReferrerPath:
    """The funnel needs to know a company page from the jobs index. It does
    not need — and must not store — an external origin."""

    @pytest.mark.parametrize(
        "raw",
        [
            "https://evil.example/steal",
            "//evil.example/steal",
            "companies/dodolab",
            "",
            None,
        ],
    )
    def test_only_same_site_paths_survive(self, raw: str | None) -> None:
        assert service.clean_referrer_path(raw) is None

    def test_rooted_path_is_kept_and_capped(self) -> None:
        assert service.clean_referrer_path("/companies/도도랩") == "/companies/도도랩"
        long_path = "/" + "a" * 500
        assert len(service.clean_referrer_path(long_path) or "") == service.MAX_REFERRER_PATH


@pytest.fixture
async def demo_jobs() -> tuple[str, uuid.UUID, uuid.UUID]:
    """A company with one open and one expired posting, cleaned up after."""
    slug = f"jobs-co-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        company = Company(
            slug=slug,
            legal_name_ko=f"주식회사 {slug}",
            display_name_ko=slug,
            aliases=[slug],
            is_demo=True,
        )
        session.add(company)
        await session.flush()

        now = datetime.now(UTC)
        open_job = _posting(
            company_id=company.id,
            source_url=f"https://example.com/{slug}/open",
            observed_at=now,
        )
        expired_job = _posting(
            company_id=company.id,
            title="마감된 공고",
            source_url=f"https://example.com/{slug}/expired",
            closes_on=(now - timedelta(days=3)).date(),
            observed_at=now - timedelta(days=1),
        )
        session.add_all([open_job, expired_job])
        await session.flush()
        ids = (company.id, open_job.id, expired_job.id)
        await session.commit()

    yield (slug, ids[1], ids[2])

    async with SessionLocal() as session:
        await session.execute(delete(Company).where(Company.slug == slug))
        await session.commit()


class TestJobListing:
    async def test_open_postings_are_listed_with_their_source(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        slug, open_id, _ = demo_jobs
        response = await client.get(f"/api/v1/companies/{slug}/jobs")
        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["id"] for item in items] == [str(open_id)]

        card = items[0]
        # Source attribution must stay on the card (docs/09 Phase 6).
        assert card["source"] == "WANTED"
        assert card["source_label"] == "원티드"
        assert card["apply_url"] == f"https://example.com/{slug}/open"
        assert card["is_open"] is True
        assert card["company"]["slug"] == slug

    async def test_expired_posting_still_resolves_by_id(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        _, _, expired_id = demo_jobs
        response = await client.get(f"/api/v1/jobs/{expired_id}")
        assert response.status_code == 200
        assert response.json()["is_open"] is False

    async def test_unknown_job_is_a_domain_404(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

    async def test_a_mangled_cursor_restarts_the_listing(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        """A cursor is an opaque token users copy around; a broken one must
        not 500."""
        slug, open_id, _ = demo_jobs
        response = await client.get(f"/api/v1/companies/{slug}/jobs?cursor=not-a-cursor")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [str(open_id)]


class TestOutboundClick:
    async def test_click_is_counted_and_returns_the_deep_link(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        slug, open_id, _ = demo_jobs
        response = await client.post(
            f"/api/v1/jobs/{open_id}/outbound-click",
            json={"referrer_path": f"/companies/{slug}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["apply_url"] == f"https://example.com/{slug}/open"
        assert body["recorded"] is True

        async with SessionLocal() as session:
            rows = (
                (
                    await session.execute(
                        select(OutboundClick).where(OutboundClick.job_id == open_id)
                    )
                )
                .scalars()
                .all()
            )
        assert len(rows) == 1
        click = rows[0]
        assert click.referrer_path == f"/companies/{slug}"
        # A salted hash, never the address itself (docs/08 §9).
        assert click.visitor_hash is not None
        assert click.visitor_hash != "127.0.0.1"
        assert click.visitor_hash == hash_ip("127.0.0.1")

    async def test_a_foreign_referrer_is_dropped_not_stored(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        _, open_id, _ = demo_jobs
        response = await client.post(
            f"/api/v1/jobs/{open_id}/outbound-click",
            json={"referrer_path": "https://evil.example/steal"},
        )
        assert response.status_code == 200

        async with SessionLocal() as session:
            path = (
                await session.execute(
                    select(OutboundClick.referrer_path).where(OutboundClick.job_id == open_id)
                )
            ).scalar_one()
        assert path is None

    async def test_repeat_clicks_count_once(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        """Apply CTR is a launch metric, so a double-click must not inflate
        it — and the second click still answers with the deep link."""
        _, open_id, _ = demo_jobs
        first = await client.post(f"/api/v1/jobs/{open_id}/outbound-click", json={})
        second = await client.post(f"/api/v1/jobs/{open_id}/outbound-click", json={})

        assert first.json()["recorded"] is True
        assert second.json()["recorded"] is False
        # Deduplicated is not an error: the user still gets sent to the job.
        assert second.status_code == 200
        assert second.json()["apply_url"] == first.json()["apply_url"]

        async with SessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count(OutboundClick.id)).where(OutboundClick.job_id == open_id)
                )
            ).scalar_one()
        assert count == 1

    async def test_click_on_an_expired_posting_is_still_accepted(
        self, client: AsyncClient, demo_jobs: tuple[str, uuid.UUID, uuid.UUID]
    ) -> None:
        """The UI hides the CTA on a closed posting, but the API does not
        pretend the link vanished — someone with the URL still gets there."""
        _, _, expired_id = demo_jobs
        response = await client.post(f"/api/v1/jobs/{expired_id}/outbound-click", json={})
        assert response.status_code == 200


class TestPostingsCreateNoMetrics:
    """The directory rule, applied to postings: a linked job establishes that
    a company is hiring. Only qualified applicant reports establish how it
    behaves."""

    async def test_seeding_postings_creates_no_reports_or_snapshots(
        self, demo_jobs: tuple[str, uuid.UUID, uuid.UUID], fresh_db: None
    ) -> None:
        slug, _, _ = demo_jobs
        async with SessionLocal() as session:
            company_id = (
                await session.execute(select(Company.id).where(Company.slug == slug))
            ).scalar_one()
            reports = (
                await session.execute(
                    select(func.count(RecruitmentExperience.id)).where(
                        RecruitmentExperience.company_id == company_id
                    )
                )
            ).scalar_one()
            snapshots = (
                await session.execute(
                    select(func.count(CompanyMetricSnapshot.id)).where(
                        CompanyMetricSnapshot.company_id == company_id
                    )
                )
            ).scalar_one()
            public_count = (
                await session.execute(
                    select(Company.public_report_count).where(Company.id == company_id)
                )
            ).scalar_one()

        assert reports == 0
        assert snapshots == 0
        assert public_count == 0


class TestFeatureFlag:
    async def test_closed_jobs_surface_reads_as_absent(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A feature that is not open should not advertise that it exists."""
        monkeypatch.setattr(settings, "enable_jobs", False)
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FEATURE_DISABLED"


class TestCardConstruction:
    def test_card_carries_sample_free_facts_only(self) -> None:
        """A job card states what the company posted. It carries no rate, so
        it can never imply a number the sample cannot support."""
        company = Company(
            id=uuid.uuid4(),
            slug="dodolab",
            legal_name_ko="주식회사 도도랩",
            display_name_ko="도도랩",
            aliases=["도도랩"],
            public_report_count=0,
            is_demo=True,
        )
        job = _posting(id=uuid.uuid4(), company_id=company.id, observed_at=datetime.now(UTC))
        card = JobCard.of(job, company, today=TODAY)
        assert "rate" not in card.model_dump()
        assert card.company.public_report_count == 0
