"""Requests to add a company the directory does not have.

The import covers 법인 with 20+ members; everyone else — a 12-person
startup, a company founded last month — reaches the directory through a
request a moderator approves. What matters: a request never becomes a
company on its own, one company is one queue entry however many ask, an
approved company is real and therefore held back by the launch gate, and
every decision is audit-logged.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from app.db.session import SessionLocal
from app.modules.companies.models import Company, CompanyAddRequest
from app.modules.companies.normalize import match_key
from app.modules.users.models import User
from app.modules.verification.models import AuditLog
from app.shared.enums import AuditAction, UserRole
from httpx import AsyncClient
from sqlalchemy import delete, select

from tests.conftest import cleanup_user

MODERATOR = "requests-moderator@example.com"


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
async def name() -> AsyncIterator[str]:
    """A company name nothing else uses, with its rows removed afterwards."""
    tag = uuid.uuid4().hex[:8]
    value = f"요청테스트{tag}"
    yield value
    async with SessionLocal() as session:
        await session.execute(
            delete(CompanyAddRequest).where(CompanyAddRequest.submitted_name.like(f"%{tag}%"))
        )
        await session.execute(delete(Company).where(Company.legal_name_ko.like(f"%{tag}%")))
        await session.commit()
    await cleanup_user(MODERATOR)


async def _request(client: AsyncClient, name: str) -> dict[str, object]:
    resp = await client.post("/api/v1/companies/request", json={"name": name})
    assert resp.status_code == 202, resp.text
    body: dict[str, object] = resp.json()
    return body


async def _company_count(name: str) -> int:
    async with SessionLocal() as session:
        rows = await session.execute(select(Company).where(Company.legal_name_ko.like(f"%{name}%")))
        return len(rows.scalars().all())


class TestRequesting:
    async def test_a_request_queues_and_creates_nothing(
        self, client: AsyncClient, name: str
    ) -> None:
        body = await _request(client, f"주식회사 {name}")
        assert body["status"] == "PENDING"
        assert await _company_count(name) == 0

    async def test_one_company_is_one_entry_however_spelled(
        self, client: AsyncClient, name: str
    ) -> None:
        first = await _request(client, f"주식회사 {name}")
        second = await _request(client, f"（주）{name}")
        assert first["id"] == second["id"]

    async def test_an_existing_company_is_pointed_to_not_queued(
        self, client: AsyncClient, name: str
    ) -> None:
        async with SessionLocal() as session:
            session.add(
                Company(
                    slug=f"req-{name}",
                    legal_name_ko=name,
                    display_name_ko=name,
                    aliases=[],
                    # As the import sets it; it is what a request is matched on.
                    match_key=match_key(name),
                )
            )
            await session.commit()
        body = await _request(client, f"{name}(주)")
        assert body["status"] == "EXISTS"
        assert body["existing_slug"] == f"req-{name}"
        assert body["id"] is None

    async def test_requests_are_rate_limited_per_visitor(
        self, client: AsyncClient, name: str
    ) -> None:
        for i in range(5):
            await _request(client, f"{name}{i}")
        resp = await client.post("/api/v1/companies/request", json={"name": f"{name}x"})
        assert resp.status_code == 429


class TestModeratorQueue:
    async def test_the_queue_is_moderator_only(self, client: AsyncClient, name: str) -> None:
        assert (await client.get("/api/v1/admin/company-requests")).status_code == 401

    async def test_approval_creates_a_real_company_held_back(
        self, client: AsyncClient, name: str
    ) -> None:
        request_id = (await _request(client, f"주식회사 {name}"))["id"]
        await _sign_in(client, MODERATOR)
        await _promote(MODERATOR)

        queue = (await client.get("/api/v1/admin/company-requests")).json()
        item = next(row for row in queue if row["id"] == request_id)
        assert "requested_by_user_id" not in item

        resp = await client.post(
            f"/api/v1/admin/company-requests/{request_id}/decision",
            json={"decision": "APPROVE"},
        )
        assert resp.status_code == 200, resp.text
        slug = resp.json()["company_slug"]

        detail = (await client.get(f"/api/v1/companies/{slug}")).json()
        assert detail["display_name_ko"] == name
        assert detail["is_demo"] is False
        assert detail["published"] is False

        async with SessionLocal() as session:
            audit = (
                (
                    await session.execute(
                        select(AuditLog).where(
                            AuditLog.action == AuditAction.COMPANY_ADD_REQUEST_DECISION,
                            AuditLog.subject_id == uuid.UUID(str(request_id)),
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert [a.payload["decision"] for a in audit] == ["APPROVE"]

    async def test_merge_links_to_an_existing_company(self, client: AsyncClient, name: str) -> None:
        request_id = (await _request(client, f"{name}코리아"))["id"]
        async with SessionLocal() as session:
            session.add(
                Company(
                    slug=f"req-{name}",
                    legal_name_ko=name,
                    display_name_ko=name,
                    aliases=[],
                    # As the import sets it; it is what a request is matched on.
                    match_key=match_key(name),
                )
            )
            await session.commit()
        await _sign_in(client, MODERATOR)
        await _promote(MODERATOR)

        resp = await client.post(
            f"/api/v1/admin/company-requests/{request_id}/decision",
            json={"decision": "MERGE", "company_slug": f"req-{name}"},
        )
        assert resp.json() == {"id": request_id, "status": "MERGED", "company_slug": f"req-{name}"}
        assert await _company_count(name) == 1

    async def test_a_decision_is_final(self, client: AsyncClient, name: str) -> None:
        request_id = (await _request(client, name))["id"]
        await _sign_in(client, MODERATOR)
        await _promote(MODERATOR)
        url = f"/api/v1/admin/company-requests/{request_id}/decision"

        assert (await client.post(url, json={"decision": "REJECT"})).status_code == 200
        again = await client.post(url, json={"decision": "APPROVE"})
        assert again.status_code == 422
        assert await _company_count(name) == 0
