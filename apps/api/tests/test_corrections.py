"""Factual correction flow — a public launch gate requirement (docs/08 §11).

The properties asserted here are the ones that make the flow safe to expose:
a company can contest a record, a contested record stops being presented as
settled, resolutions move the aggregates, and at no point does the reporter's
identity appear anywhere in the flow.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.db.session import SessionLocal
from app.modules.companies.models import Company
from app.modules.company_claims.models import CorrectionRequest
from app.modules.reports.models import RecruitmentExperience
from app.modules.verification.models import AuditLog
from app.shared.enums import AuditAction, UserRole, VerificationStatus
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import cleanup_user


async def _company(slug: str) -> uuid.UUID:
    async with SessionLocal() as session:
        company = Company(
            slug=slug,
            legal_name_ko="정정테스트 주식회사",
            display_name_ko="정정테스트",
            aliases=["정정테스트"],
            is_demo=True,
        )
        session.add(company)
        await session.commit()
        return company.id


async def _sign_in(client: AsyncClient, email: str) -> None:
    resp = await client.post("/api/v1/auth/sign-in", json={"email": email})
    token = resp.json()["dev_token"]
    await client.post("/api/v1/auth/verify", json={"token": token})


async def _promote(email: str, role: UserRole) -> None:
    from app.modules.users.models import User

    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.role = role
        await session.commit()


async def _verified_report(client: AsyncClient, company_id: uuid.UUID) -> str:
    """Files a report and pushes it to VERIFIED, the state a company would
    actually be contesting."""
    interaction = datetime.now(UTC) - timedelta(days=45)
    draft = await client.post(
        "/api/v1/reports",
        json={
            "company_id": str(company_id),
            "role_title": "프론트엔드 개발자",
            "role_category": "SOFTWARE_ENGINEERING",
            "employment_type": "FULL_TIME",
            "source": "COMPANY_SITE",
            "application_date": (interaction - timedelta(days=10)).date().isoformat(),
            "furthest_stage": "INTERVIEW_1",
            "last_company_interaction_at": interaction.isoformat(),
            "result_received": False,
            "outcome": "UNKNOWN",
        },
    )
    report_id = draft.json()["id"]
    await client.post(f"/api/v1/reports/{report_id}/submit")
    async with SessionLocal() as session:
        report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
        assert report is not None
        report.verification_status = VerificationStatus.VERIFIED
        await session.commit()
    return report_id


async def _cleanup_company(slug: str) -> None:
    from sqlalchemy import delete

    async with SessionLocal() as session:
        company = (
            await session.execute(select(Company).where(Company.slug == slug))
        ).scalar_one_or_none()
        if company is not None:
            await session.execute(
                delete(CorrectionRequest).where(CorrectionRequest.company_id == company.id)
            )
            await session.execute(delete(Company).where(Company.id == company.id))
        await session.commit()


class TestCorrectionSubmission:
    async def test_company_can_contest_a_record_without_an_account(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        """The correction route must work, not merely exist — so it does not
        require a verified claim first."""
        company_id = await _company(clean_slice)
        email = "correction-reporter@example.com"
        try:
            await _sign_in(client, email)
            report_id = await _verified_report(client, company_id)
            await client.post("/api/v1/auth/sign-out")

            resp = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": report_id,
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "해당 지원자에게 2026-07-10에 불합격 메일을 발송했습니다.",
                    "disputed_fields": ["result_received"],
                },
            )
            assert resp.status_code == 202, resp.text

            # A contested record stops being presented as settled.
            async with SessionLocal() as session:
                report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
                assert report is not None
                assert report.verification_status is VerificationStatus.DISPUTED
        finally:
            await cleanup_user(email)
            await _cleanup_company(clean_slice)

    async def test_rejects_a_field_that_is_not_the_company_s_to_assert(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        """outcome and free_context are the applicant's own account; a company
        cannot 'correct' them."""
        await _company(clean_slice)
        try:
            resp = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "지원자의 서술이 사실과 다릅니다.",
                    "disputed_fields": ["free_context", "outcome"],
                },
            )
            assert resp.status_code == 422
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        finally:
            await _cleanup_company(clean_slice)

    async def test_cannot_probe_for_reports_on_another_company(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        await _company(clean_slice)
        try:
            resp = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": str(uuid.uuid4()),
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "존재하지 않는 기록에 대한 정정 요청입니다.",
                },
            )
            assert resp.status_code == 404
        finally:
            await _cleanup_company(clean_slice)


class TestCorrectionResolution:
    async def test_correcting_a_field_restores_the_record_and_recomputes(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        company_id = await _company(clean_slice)
        reporter, mod = "corr-reporter2@example.com", "corr-mod@example.com"
        try:
            await _sign_in(client, reporter)
            report_id = await _verified_report(client, company_id)
            await client.post("/api/v1/auth/sign-out")

            submit = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": report_id,
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "결과 메일을 발송한 기록이 있습니다.",
                    "disputed_fields": ["result_received"],
                },
            )
            request_id = submit.json()["id"]

            await _sign_in(client, mod)
            await _promote(mod, UserRole.MODERATOR)

            queue = await client.get("/api/v1/admin/disputes")
            assert queue.status_code == 200
            assert any(d["id"] == request_id for d in queue.json())

            decide = await client.post(
                f"/api/v1/admin/disputes/{request_id}/decision",
                json={
                    "outcome": "CORRECTED",
                    "decision_note": "발송 로그 확인",
                    "field_corrections": {
                        "result_received": True,
                        "result_received_at": "2026-07-10T00:00:00+00:00",
                    },
                },
            )
            assert decide.status_code == 200, decide.text

            async with SessionLocal() as session:
                report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
                assert report is not None
                assert report.result_received is True
                assert report.result_received_at is not None
                # Corrected, not discarded: the observation still counts.
                assert report.verification_status is VerificationStatus.VERIFIED
        finally:
            await cleanup_user(reporter)
            await cleanup_user(mod)
            await _cleanup_company(clean_slice)

    async def test_upholding_restores_a_disputed_record(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        company_id = await _company(clean_slice)
        reporter, mod = "corr-reporter3@example.com", "corr-mod3@example.com"
        try:
            await _sign_in(client, reporter)
            report_id = await _verified_report(client, company_id)
            await client.post("/api/v1/auth/sign-out")

            submit = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": report_id,
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "기록이 사실과 다르다고 생각합니다.",
                },
            )
            await _sign_in(client, mod)
            await _promote(mod, UserRole.MODERATOR)
            await client.post(
                f"/api/v1/admin/disputes/{submit.json()['id']}/decision",
                json={"outcome": "UPHELD", "decision_note": "원 기록이 정확함"},
            )

            async with SessionLocal() as session:
                report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
                assert report is not None
                # Must not be left stranded in DISPUTED after review.
                assert report.verification_status is VerificationStatus.VERIFIED
        finally:
            await cleanup_user(reporter)
            await cleanup_user(mod)
            await _cleanup_company(clean_slice)

    async def test_removal_reverses_the_contributor_s_standing(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        from app.modules.reputation.models import ReputationEvent
        from app.modules.users.models import User

        company_id = await _company(clean_slice)
        reporter, mod = "corr-reporter4@example.com", "corr-mod4@example.com"
        try:
            await _sign_in(client, reporter)
            report_id = await _verified_report(client, company_id)
            async with SessionLocal() as session:
                user = (
                    await session.execute(select(User).where(User.email == reporter))
                ).scalar_one()
                user.verified_contribution_count = 1
                user.reputation_score = 25
                await session.commit()
            await client.post("/api/v1/auth/sign-out")

            submit = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": report_id,
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "해당 지원 이력이 존재하지 않습니다.",
                },
            )
            await _sign_in(client, mod)
            await _promote(mod, UserRole.MODERATOR)
            await client.post(
                f"/api/v1/admin/disputes/{submit.json()['id']}/decision",
                json={"outcome": "REMOVED", "decision_note": "지원 이력 확인 불가"},
            )

            async with SessionLocal() as session:
                report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
                assert report is not None
                assert report.verification_status is VerificationStatus.REMOVED

                user = (
                    await session.execute(select(User).where(User.email == reporter))
                ).scalar_one()
                assert user.reversed_contribution_count == 1

                events = (
                    (
                        await session.execute(
                            select(ReputationEvent).where(ReputationEvent.user_id == user.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                assert any(e.delta < 0 for e in events), "reversal must be on the ledger"
        finally:
            await cleanup_user(reporter)
            await cleanup_user(mod)
            await _cleanup_company(clean_slice)

    async def test_a_resolved_request_cannot_be_decided_twice(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        await _company(clean_slice)
        mod = "corr-mod5@example.com"
        try:
            submit = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "회사 페이지 전반에 대한 정정 요청입니다.",
                },
            )
            request_id = submit.json()["id"]
            await _sign_in(client, mod)
            await _promote(mod, UserRole.MODERATOR)

            first = await client.post(
                f"/api/v1/admin/disputes/{request_id}/decision",
                json={"outcome": "REJECTED"},
            )
            assert first.status_code == 200
            second = await client.post(
                f"/api/v1/admin/disputes/{request_id}/decision",
                json={"outcome": "UPHELD"},
            )
            assert second.status_code == 422
        finally:
            await cleanup_user(mod)
            await _cleanup_company(clean_slice)


class TestCorrectionPrivacy:
    async def test_nothing_in_the_flow_exposes_the_reporter(
        self, client: AsyncClient, clean_slice: str
    ) -> None:
        """docs/08 §4: a company challenges the record, never the person."""
        company_id = await _company(clean_slice)
        reporter, mod = "corr-secret@example.com", "corr-mod6@example.com"
        try:
            await _sign_in(client, reporter)
            report_id = await _verified_report(client, company_id)

            async with SessionLocal() as session:
                report = await session.get(RecruitmentExperience, uuid.UUID(report_id))
                assert report is not None
                reporter_id = str(report.user_id)
            await client.post("/api/v1/auth/sign-out")

            submit = await client.post(
                f"/api/v1/companies/{clean_slice}/corrections",
                json={
                    "experience_id": report_id,
                    "contact_email": "hr@company.example.com",
                    "claim_summary": "기록의 사실관계를 확인하고자 합니다.",
                },
            )
            assert reporter_id not in submit.text

            await _sign_in(client, mod)
            await _promote(mod, UserRole.MODERATOR)
            queue = await client.get("/api/v1/admin/disputes")
            # Even the moderator's dispute queue carries no reporter id.
            assert reporter_id not in queue.text

            async with SessionLocal() as session:
                logs = (
                    (
                        await session.execute(
                            select(AuditLog).where(
                                AuditLog.action == AuditAction.COMPANY_CORRECTION
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for entry in logs:
                    assert reporter_id not in str(entry.payload)
        finally:
            await cleanup_user(reporter)
            await cleanup_user(mod)
            await _cleanup_company(clean_slice)
