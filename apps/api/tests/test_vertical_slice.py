"""The handoff's definition of done, executed as one test.

A new user can: open the site, find a company with no data, sign in, submit a
structured experience, attach private evidence, have a moderator verify it,
see the company's aggregates recompute, and see their own contribution
recorded in the reputation ledger.

Anything that breaks this loop breaks the product, so it is asserted
end-to-end through the HTTP API rather than against services directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.db.session import SessionLocal
from app.modules.companies.models import Company
from app.modules.evidence.models import Evidence, EvidenceAccessLog
from app.modules.reputation.models import ReputationEvent
from app.modules.users.models import User
from app.shared.enums import (
    EvidenceAccessState,
    EvidenceReviewState,
    HiringStage,
    MetricEligibility,
    ReputationEventType,
    UserRole,
)
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import cleanup_user


async def _make_company(slug: str) -> uuid.UUID:
    async with SessionLocal() as session:
        company = Company(
            slug=slug,
            legal_name_ko="주식회사 검증테스트",
            display_name_ko="검증테스트",
            name_en="Verify Test",
            aliases=["검증테스트"],
            industry="소프트웨어",
            is_demo=True,
        )
        session.add(company)
        await session.commit()
        return company.id


async def _sign_in(client: AsyncClient, email: str) -> None:
    resp = await client.post("/api/v1/auth/sign-in", json={"email": email})
    assert resp.status_code == 202
    token = resp.json()["dev_token"]
    assert token, "dev_token must be returned outside production"
    verify = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verify.status_code == 200


async def _promote(email: str, role: UserRole) -> None:
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.role = role
        await session.commit()


class TestVerticalSlice:
    async def test_full_contribution_loop(self, client: AsyncClient, clean_slice: str) -> None:
        slug = clean_slice
        company_id = await _make_company(slug)
        contributor_email = "slice-contributor@example.com"
        moderator_email = "slice-moderator@example.com"

        try:
            # 2-3. The company is findable and honestly reports having no data.
            search = await client.get("/api/v1/companies/search", params={"q": "검증테스트"})
            assert search.status_code == 200
            assert any(c["slug"] == slug for c in search.json())

            metrics = await client.get(f"/api/v1/companies/{slug}/metrics")
            assert metrics.status_code == 200
            empty = metrics.json()
            assert empty["eligibility"] == MetricEligibility.INSUFFICIENT_DATA
            assert empty["qualified_n"] == 0
            # No data must never be rendered as a zero rate.
            assert empty["ghost_rate"] is None
            assert empty["response_rate"] is None

            # 4. Authenticate.
            await _sign_in(client, contributor_email)
            me = await client.get("/api/v1/auth/me")
            assert me.status_code == 200

            # 5. Submit a structured experience.
            interaction = datetime.now(UTC) - timedelta(days=40)
            draft = await client.post(
                "/api/v1/reports",
                json={
                    "company_id": str(company_id),
                    "role_title": "프론트엔드 개발자",
                    "role_category": "SOFTWARE_ENGINEERING",
                    "employment_type": "FULL_TIME",
                    "source": "COMPANY_SITE",
                    "application_date": (interaction - timedelta(days=20)).date().isoformat(),
                    "furthest_stage": HiringStage.INTERVIEW_1.value,
                    "last_company_interaction_at": interaction.isoformat(),
                    "promised_result": True,
                    "promised_result_date": (interaction + timedelta(days=7)).date().isoformat(),
                    "result_received": False,
                    "outcome": "UNKNOWN",
                    "context": None,
                },
                headers={"X-Idempotency-Key": uuid.uuid4().hex},
            )
            assert draft.status_code == 201, draft.text
            report_id = draft.json()["id"]
            assert draft.json()["verification_status"] == "DRAFT"

            # The contributor's own list names the company, or one card
            # cannot be told from another.
            mine = await client.get("/api/v1/me/reports")
            assert mine.status_code == 200
            row = next(r for r in mine.json() if r["id"] == report_id)
            assert row["company_slug"] == slug
            assert row["company_name"] == "검증테스트"

            # 6. Attach evidence privately.
            intent = await client.post(
                f"/api/v1/reports/{report_id}/evidence/upload-intent",
                json={
                    "content_type": "image/png",
                    "size_bytes": 2048,
                    "kind": "RESULT_EMAIL",
                    "original_filename": "result.png",
                },
            )
            assert intent.status_code == 201, intent.text
            intent_body = intent.json()
            evidence_id = intent_body["evidence_id"]
            assert intent_body["upload_url"]
            # The response must not hand the client a bucket key.
            assert "object_key" not in intent.text

            listed = await client.get(f"/api/v1/reports/{report_id}/evidence")
            assert listed.status_code == 200
            assert "object_key" not in listed.text

            submitted = await client.post(f"/api/v1/reports/{report_id}/submit")
            assert submitted.status_code == 200, submitted.text
            # A promise past its grace period routes to review.
            assert submitted.json()["verification_status"] in (
                "AUTO_CHECKED",
                "NEEDS_REVIEW",
            )

            # Mark the evidence as uploaded and clean, as the upload callback
            # and a PII pass would.
            async with SessionLocal() as session:
                evidence = await session.get(Evidence, uuid.UUID(evidence_id))
                assert evidence is not None
                evidence.access_state = EvidenceAccessState.AVAILABLE
                evidence.review_state = EvidenceReviewState.CLEAN
                await session.commit()

            # 7. A moderator verifies it.
            await client.post("/api/v1/auth/sign-out")
            await _sign_in(client, moderator_email)
            await _promote(moderator_email, UserRole.MODERATOR)

            queue = await client.get("/api/v1/admin/reports")
            assert queue.status_code == 200
            assert any(item["id"] == report_id for item in queue.json())

            decision = await client.post(
                f"/api/v1/admin/reports/{report_id}/decision",
                json={"decision": "VERIFY", "reasons": ["evidence_consistent"]},
            )
            assert decision.status_code == 200, decision.text
            assert decision.json()["verification_status"] == "VERIFIED"

            # 8-9. Aggregates recomputed; the company page reflects it.
            metrics_after = await client.get(f"/api/v1/companies/{slug}/metrics")
            body = metrics_after.json()
            assert body["qualified_n"] == 1
            assert body["verified_ratio"] == 1.0
            # One observation is still far below the publishable bar, so no
            # rate is published even though the observation is real.
            assert body["eligibility"] == MetricEligibility.INSUFFICIENT_DATA
            assert body["ghost_rate"] is None

            public_reports = await client.get(f"/api/v1/companies/{slug}/reports")
            assert public_reports.status_code == 200
            cards = public_reports.json()
            assert len(cards) == 1
            # The public card must not identify the reporter.
            assert "user_id" not in cards[0]

            # 10. The contribution is in the reputation ledger.
            async with SessionLocal() as session:
                contributor = (
                    await session.execute(select(User).where(User.email == contributor_email))
                ).scalar_one()
                events = (
                    (
                        await session.execute(
                            select(ReputationEvent).where(ReputationEvent.user_id == contributor.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                types = {e.event_type for e in events}
                assert ReputationEventType.REPORT_SUBMITTED_COMPLETE in types
                assert ReputationEventType.REPORT_VERIFIED in types
                assert ReputationEventType.EVIDENCE_VERIFIED in types
                assert contributor.reputation_score > 0
                assert contributor.verified_contribution_count == 1
                # The ledger balances match the running total on the user.
                latest = max(events, key=lambda e: e.created_at)
                assert latest.balance_after == contributor.reputation_score
        finally:
            await cleanup_user(contributor_email)
            await cleanup_user(moderator_email)


class TestEvidencePrivacy:
    async def test_moderator_access_is_logged(self, client: AsyncClient, clean_slice: str) -> None:
        """Every issuance of a signed evidence URL must leave an audit trail."""
        slug = clean_slice
        company_id = await _make_company(slug)
        contributor_email = "slice-priv-user@example.com"
        moderator_email = "slice-priv-mod@example.com"
        try:
            await _sign_in(client, contributor_email)
            draft = await client.post(
                "/api/v1/reports",
                json={
                    "company_id": str(company_id),
                    "role_title": "백엔드 개발자",
                    "role_category": "SOFTWARE_ENGINEERING",
                    "employment_type": "FULL_TIME",
                    "source": "WANTED",
                    "application_date": (datetime.now(UTC) - timedelta(days=60)).date().isoformat(),
                    "furthest_stage": "TEST",
                    "result_received": False,
                    "outcome": "UNKNOWN",
                },
            )
            report_id = draft.json()["id"]
            intent = await client.post(
                f"/api/v1/reports/{report_id}/evidence/upload-intent",
                json={"content_type": "image/png", "size_bytes": 1024},
            )
            evidence_id = intent.json()["evidence_id"]

            await client.post("/api/v1/auth/sign-out")
            await _sign_in(client, moderator_email)
            await _promote(moderator_email, UserRole.MODERATOR)

            view = await client.get(f"/api/v1/admin/evidence/{evidence_id}")
            assert view.status_code == 200, view.text
            assert view.json()["signed_url"].startswith("http")

            async with SessionLocal() as session:
                logs = (
                    (
                        await session.execute(
                            select(EvidenceAccessLog).where(
                                EvidenceAccessLog.evidence_id == uuid.UUID(evidence_id)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(logs) == 1
                assert logs[0].purpose == "moderation_review"
        finally:
            await cleanup_user(contributor_email)
            await cleanup_user(moderator_email)

    async def test_non_moderator_cannot_view_evidence(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        company_id = await _make_company(clean_slice)
        email = "slice-nosy@example.com"
        try:
            await _sign_in(client, email)
            draft = await client.post(
                "/api/v1/reports",
                json={
                    "company_id": str(company_id),
                    "role_title": "디자이너",
                    "role_category": "DESIGN",
                    "employment_type": "FULL_TIME",
                    "source": "WANTED",
                    "application_date": (datetime.now(UTC) - timedelta(days=50)).date().isoformat(),
                    "furthest_stage": "APPLICATION",
                    "result_received": False,
                    "outcome": "UNKNOWN",
                },
            )
            intent = await client.post(
                f"/api/v1/reports/{draft.json()['id']}/evidence/upload-intent",
                json={"content_type": "image/png", "size_bytes": 1024},
            )
            evidence_id = intent.json()["evidence_id"]
            denied = await client.get(f"/api/v1/admin/evidence/{evidence_id}")
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "FORBIDDEN"
        finally:
            await cleanup_user(email)


class TestDuplicateProtection:
    async def test_same_process_cannot_be_reported_twice(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        company_id = await _make_company(clean_slice)
        email = "slice-dupe@example.com"
        payload = {
            "company_id": str(company_id),
            "role_title": "데이터 분석가",
            "role_category": "DATA",
            "employment_type": "FULL_TIME",
            "source": "JOBKOREA",
            "application_date": (datetime.now(UTC) - timedelta(days=70)).date().isoformat(),
            "furthest_stage": "DOCUMENT_SCREENING",
            "result_received": False,
            "outcome": "UNKNOWN",
        }
        try:
            await _sign_in(client, email)
            first = await client.post("/api/v1/reports", json=payload)
            assert (
                await client.post(f"/api/v1/reports/{first.json()['id']}/submit")
            ).status_code == 200

            second = await client.post("/api/v1/reports", json=payload)
            dupe = await client.post(f"/api/v1/reports/{second.json()['id']}/submit")
            assert dupe.status_code == 409
            assert dupe.json()["error"]["code"] == "DUPLICATE_REPORT"
        finally:
            await cleanup_user(email)

    async def test_idempotency_key_returns_same_draft(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        """A retried create must not leave two drafts behind."""
        company_id = await _make_company(clean_slice)
        email = "slice-idem@example.com"
        key = uuid.uuid4().hex
        payload = {
            "company_id": str(company_id),
            "role_title": "PM",
            "role_category": "PRODUCT",
            "employment_type": "FULL_TIME",
            "source": "REFERRAL",
            "application_date": (datetime.now(UTC) - timedelta(days=30)).date().isoformat(),
            "furthest_stage": "APPLICATION",
            "result_received": False,
            "outcome": "UNKNOWN",
        }
        try:
            await _sign_in(client, email)
            a = await client.post(
                "/api/v1/reports", json=payload, headers={"X-Idempotency-Key": key}
            )
            b = await client.post(
                "/api/v1/reports", json=payload, headers={"X-Idempotency-Key": key}
            )
            assert a.json()["id"] == b.json()["id"]
        finally:
            await cleanup_user(email)


class TestAuthBoundaries:
    async def test_anonymous_cannot_create_report(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/reports", json={})
        assert resp.status_code in (401, 422)

    async def test_anonymous_cannot_read_admin_queue(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/admin/reports")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"
