"""The quick log: many companies in one submission.

One applicant has usually applied to dozens of companies, and the wizard
takes eight steps per company. The quick log files one short line per
company through the same draft-and-submit path. What matters: every
safeguard of a single report still holds per line, a bad line does not sink
the rest, a line cannot claim more silence than happened, and a moderator
can approve the clean lines together without ever covering a flagged one.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
from app.db.session import SessionLocal
from app.modules.companies.models import Company
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.reports.models import RecruitmentExperience
from app.modules.reputation.models import ReputationEvent
from app.modules.users.models import User
from app.shared.enums import UserRole, VerificationStatus
from httpx import AsyncClient
from sqlalchemy import delete, select

from tests.conftest import cleanup_user

CONTRIBUTOR = "quicklog-contributor@example.com"
MODERATOR = "quicklog-moderator@example.com"
DEFAULTS = {
    "role_title": "백엔드 개발자",
    "role_category": "SOFTWARE_ENGINEERING",
    "employment_type": "FULL_TIME",
    "source": "WANTED",
}


async def _sign_in(client: AsyncClient, email: str) -> None:
    resp = await client.post("/api/v1/auth/sign-in", json={"email": email})
    token = resp.json()["dev_token"]
    assert (await client.post("/api/v1/auth/verify", json={"token": token})).status_code == 200


async def _promote(email: str) -> None:
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.role = UserRole.MODERATOR
        await session.commit()


@pytest.fixture
async def companies(client: AsyncClient) -> AsyncIterator[list[str]]:
    tag = uuid.uuid4().hex[:8]
    ids: list[uuid.UUID] = []
    async with SessionLocal() as session:
        for i in range(3):
            company = Company(
                slug=f"quick-{tag}-{i}",
                legal_name_ko=f"빠른기록{tag}{i}",
                display_name_ko=f"빠른기록{tag}{i}",
                aliases=[],
                is_demo=True,
            )
            session.add(company)
            await session.flush()
            ids.append(company.id)
        await session.commit()
    yield [str(i) for i in ids]
    await cleanup_user(CONTRIBUTOR)
    await cleanup_user(MODERATOR)
    async with SessionLocal() as session:
        await session.execute(
            delete(CompanyMetricSnapshot).where(CompanyMetricSnapshot.company_id.in_(ids))
        )
        await session.execute(delete(Company).where(Company.id.in_(ids)))
        await session.commit()


def _line(company_id: str, **overrides: object) -> dict[str, object]:
    applied = date.today() - timedelta(days=70)
    line: dict[str, object] = {
        "company_id": company_id,
        "application_date": applied.isoformat(),
        "furthest_stage": "APPLICATION",
        "result_received": False,
    }
    line.update(overrides)
    return line


async def _batch(client: AsyncClient, items: list[dict[str, object]]) -> dict[str, object]:
    resp = await client.post("/api/v1/reports/batch", json={"defaults": DEFAULTS, "items": items})
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


class TestFiling:
    async def test_each_line_becomes_a_report_in_one_batch(
        self, client: AsyncClient, companies: list[str]
    ) -> None:
        await _sign_in(client, CONTRIBUTOR)
        rejected_on = (date.today() - timedelta(days=50)).isoformat()
        body = await _batch(
            client,
            [
                _line(companies[0]),
                _line(
                    companies[1],
                    furthest_stage="INTERVIEW_1",
                    last_company_interaction_on=(date.today() - timedelta(days=55)).isoformat(),
                    result_received=True,
                    result_received_on=rejected_on,
                    outcome="REJECTED",
                ),
            ],
        )
        assert body["submitted"] == 2

        async with SessionLocal() as session:
            reports = (
                (
                    await session.execute(
                        select(RecruitmentExperience).where(
                            RecruitmentExperience.batch_id == uuid.UUID(str(body["batch_id"]))
                        )
                    )
                )
                .scalars()
                .all()
            )
            awarded = (
                (
                    await session.execute(
                        select(ReputationEvent).where(
                            ReputationEvent.subject_id.in_([r.id for r in reports])
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert len(reports) == 2
        assert {r.role_title for r in reports} == {"백엔드 개발자"}
        assert all(r.verification_status is VerificationStatus.AUTO_CHECKED for r in reports)
        # Standing comes from verification, not from filing thin lines.
        assert awarded == []

    async def test_a_line_past_the_application_needs_its_last_contact(
        self, client: AsyncClient, companies: list[str]
    ) -> None:
        """Without it the silence clock would start at the application and
        count weeks the company was actually in touch."""
        await _sign_in(client, CONTRIBUTOR)
        resp = await client.post(
            "/api/v1/reports/batch",
            json={
                "defaults": DEFAULTS,
                "items": [_line(companies[0], furthest_stage="INTERVIEW_1")],
            },
        )
        assert resp.status_code == 422

    async def test_a_bad_line_does_not_sink_the_rest(
        self, client: AsyncClient, companies: list[str]
    ) -> None:
        await _sign_in(client, CONTRIBUTOR)
        body = await _batch(
            client,
            [
                _line(companies[0]),
                _line(companies[0]),  # same company, stage, month
                _line(str(uuid.uuid4())),  # no such company
                _line(companies[1]),
            ],
        )
        statuses = [r["status"] for r in body["results"]]  # type: ignore[union-attr, index]
        assert statuses == ["SUBMITTED", "DUPLICATE", "INVALID", "SUBMITTED"]
        assert body["submitted"] == 2

    async def test_thirty_lines_at_most(self, client: AsyncClient, companies: list[str]) -> None:
        await _sign_in(client, CONTRIBUTOR)
        resp = await client.post(
            "/api/v1/reports/batch",
            json={"defaults": DEFAULTS, "items": [_line(companies[0])] * 31},
        )
        assert resp.status_code == 422


class TestBatchReview:
    async def test_approval_covers_clean_lines_and_leaves_flagged_ones(
        self, client: AsyncClient, companies: list[str]
    ) -> None:
        await _sign_in(client, CONTRIBUTOR)
        applied = date.today() - timedelta(days=70)
        body = await _batch(
            client,
            [
                _line(companies[0]),
                _line(companies[1]),
                # Contacted before applying: the auto-checks flag it.
                _line(
                    companies[2],
                    furthest_stage="INTERVIEW_1",
                    last_company_interaction_on=(applied - timedelta(days=5)).isoformat(),
                ),
            ],
        )
        batch_id = body["batch_id"]

        await _sign_in(client, MODERATOR)
        await _promote(MODERATOR)
        queue = (await client.get("/api/v1/admin/reports")).json()
        assert sum(1 for row in queue if row["batch_id"] == batch_id) == 3

        resp = await client.post(
            f"/api/v1/admin/report-batches/{batch_id}/decision",
            json={"decision": "PARTIALLY_VERIFY"},
        )
        assert resp.json() == {"decided": 2, "left_for_review": 1}

        async with SessionLocal() as session:
            statuses = sorted(
                (
                    await session.execute(
                        select(RecruitmentExperience.verification_status).where(
                            RecruitmentExperience.batch_id == uuid.UUID(str(batch_id))
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert statuses == sorted(
            [
                VerificationStatus.PARTIALLY_VERIFIED,
                VerificationStatus.PARTIALLY_VERIFIED,
                VerificationStatus.NEEDS_REVIEW,
            ]
        )

    async def test_batch_review_is_moderator_only(
        self, client: AsyncClient, companies: list[str]
    ) -> None:
        await _sign_in(client, CONTRIBUTOR)
        body = await _batch(client, [_line(companies[0])])
        resp = await client.post(
            f"/api/v1/admin/report-batches/{body['batch_id']}/decision",
            json={"decision": "PARTIALLY_VERIFY"},
        )
        assert resp.status_code == 403
