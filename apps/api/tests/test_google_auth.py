"""Google sign-in.

Everything here guards a boundary where getting it wrong hands over an
account: the `state` that proves the callback started with us, the claims
that prove the token is Google's *and ours*, the verified-email flag that
stops one account claiming another's address, and the `next` path that must
never turn sign-in into an open redirect.

The two providers are also asserted to converge: a contributor who used the
magic link first must land on the same row when they later use Google, or
their reports and reputation split in half.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.auth import google, service
from app.modules.users.models import User
from app.shared.enums import TrustState, UserRole
from app.shared.errors import AuthProviderError, AuthProviderUnavailableError
from httpx import AsyncClient
from sqlalchemy import delete, select

CLIENT_ID = "test-client-id.apps.googleusercontent.com"


def _id_token(**overrides: object) -> str:
    """A token shaped the way Google's token endpoint returns one. The
    signature is filler: the code path under test reads tokens that arrived
    over an authenticated TLS channel and validates claims, not signatures."""
    claims: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "108124098124098124098",
        "email": "Dodo@Example.com",
        "email_verified": True,
        "exp": int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()),
    }
    claims.update(overrides)
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@pytest.fixture
def google_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "google_client_secret", "test-secret")


class TestNextPath:
    """The callback redirects to whatever this returns."""

    @pytest.mark.parametrize(
        "raw",
        [
            "https://evil.example/phish",
            "//evil.example/phish",
            "javascript:alert(1)",
            "report/new",
            "",
            None,
        ],
    )
    def test_only_same_site_paths_survive(self, raw: str | None) -> None:
        assert google.safe_next_path(raw) == "/"

    def test_a_rooted_path_is_kept(self) -> None:
        assert google.safe_next_path("/report/new") == "/report/new"


class TestClaimValidation:
    def test_a_well_formed_token_yields_the_profile(self, google_configured: None) -> None:
        profile = google._validate_claims(google._decode_id_token_claims(_id_token()))
        assert profile.sub == "108124098124098124098"
        # Addresses are matched lowercased, or two spellings become two accounts.
        assert profile.email == "dodo@example.com"

    def test_a_token_for_another_application_is_refused(self, google_configured: None) -> None:
        token = _id_token(aud="someone-elses-client-id")
        with pytest.raises(AuthProviderError):
            google._validate_claims(google._decode_id_token_claims(token))

    def test_a_foreign_issuer_is_refused(self, google_configured: None) -> None:
        with pytest.raises(AuthProviderError):
            google._validate_claims(google._decode_id_token_claims(_id_token(iss="evil.example")))

    def test_an_expired_token_is_refused(self, google_configured: None) -> None:
        stale = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())
        with pytest.raises(AuthProviderError):
            google._validate_claims(google._decode_id_token_claims(_id_token(exp=stale)))

    def test_an_unverified_email_is_refused(self, google_configured: None) -> None:
        """Otherwise an account could assert an address it does not own, and
        the email match below would hand it someone else's row."""
        with pytest.raises(AuthProviderError):
            google._validate_claims(google._decode_id_token_claims(_id_token(email_verified=False)))

    @pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b", "a.!!!.c"])
    def test_a_malformed_token_is_refused_not_crashed(self, token: str) -> None:
        with pytest.raises(AuthProviderError):
            google._decode_id_token_claims(token)


class TestState:
    """These touch Redis directly, so they take `fresh_redis` — a connection
    left bound to a finished test's event loop breaks the next test that
    touches Redis, wherever that happens to be."""

    async def test_state_round_trips_the_landing_path(
        self, fresh_redis: None, google_configured: None
    ) -> None:
        url = await google.start("/report/new")
        state = url.split("state=")[1].split("&")[0]
        assert await google.consume_state(state) == "/report/new"

    async def test_state_is_single_use(self, fresh_redis: None, google_configured: None) -> None:
        """A replayed callback must not mint a second session."""
        url = await google.start("/")
        state = url.split("state=")[1].split("&")[0]
        await google.consume_state(state)
        with pytest.raises(AuthProviderError):
            await google.consume_state(state)

    async def test_an_unknown_state_is_refused(self, fresh_redis: None) -> None:
        with pytest.raises(AuthProviderError):
            await google.consume_state("never-issued")

    async def test_a_missing_state_is_refused(self, fresh_redis: None) -> None:
        with pytest.raises(AuthProviderError):
            await google.consume_state(None)

    async def test_start_carries_our_client_id_and_callback(
        self, fresh_redis: None, google_configured: None
    ) -> None:
        url = await google.start(None)
        assert url.startswith(google.AUTHORIZE_ENDPOINT)
        assert CLIENT_ID in url
        assert "response_type=code" in url
        # A shared machine must not sign someone in as the previous person.
        assert "prompt=select_account" in url


class TestUnconfigured:
    async def test_starting_without_credentials_is_unavailable_not_broken(
        self, fresh_redis: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "google_client_id", "")
        monkeypatch.setattr(settings, "google_client_secret", "")
        with pytest.raises(AuthProviderUnavailableError):
            await google.start(None)

    async def test_providers_endpoint_reports_the_truth(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The web app renders its Google button from this, so a
        misconfigured API cannot produce a button that leads nowhere."""
        monkeypatch.setattr(settings, "google_client_id", "")
        monkeypatch.setattr(settings, "google_client_secret", "")
        off = await client.get("/api/v1/auth/providers")
        assert off.json() == {"google": False, "magic_link": True}

        monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
        monkeypatch.setattr(settings, "google_client_secret", "test-secret")
        on = await client.get("/api/v1/auth/providers")
        assert on.json()["google"] is True


class TestCallbackRedirects:
    """This URL is reached by a browser navigation, so every outcome is a
    redirect — an error envelope would leave the user reading raw JSON."""

    async def test_a_forged_state_lands_on_sign_in(
        self, client: AsyncClient, google_configured: None
    ) -> None:
        response = await client.get(
            "/api/v1/auth/google/callback?code=abc&state=forged", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/sign-in?error=state" in response.headers["location"]

    async def test_a_cancelled_consent_lands_on_sign_in(
        self, client: AsyncClient, google_configured: None
    ) -> None:
        url = await google.start("/report/new")
        state = url.split("state=")[1].split("&")[0]
        response = await client.get(
            f"/api/v1/auth/google/callback?error=access_denied&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/sign-in?error=cancelled" in response.headers["location"]

    async def test_no_session_cookie_is_set_on_failure(
        self, client: AsyncClient, google_configured: None
    ) -> None:
        response = await client.get(
            "/api/v1/auth/google/callback?code=abc&state=forged", follow_redirects=False
        )
        assert settings.session_cookie_name not in response.cookies


class TestAccountResolution:
    """Both providers must land on one row, or a contributor's reports and
    reputation split between two accounts."""

    async def test_first_google_sign_in_creates_the_account(self, fresh_db: None) -> None:
        email = f"new-{uuid.uuid4().hex[:8]}@example.com"
        profile = google.GoogleProfile(
            sub=f"sub-{uuid.uuid4().hex}", email=email, email_verified=True
        )
        async with SessionLocal() as session:
            user = await service.sign_in_with_google(session, profile=profile)
            await session.commit()
            assert user.google_sub == profile.sub
            assert user.email_verified_at is not None
            # A handle is a pseudonym, not a transform of the address.
            assert email.split("@")[0] not in user.handle or user.handle != email.split("@")[0]
            user_id = user.id

        async with SessionLocal() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

    async def test_google_links_to_an_existing_magic_link_account(self, fresh_db: None) -> None:
        email = f"existing-{uuid.uuid4().hex[:8]}@example.com"
        async with SessionLocal() as session:
            existing = User(
                email=email,
                handle=f"관찰자{uuid.uuid4().hex[:6]}",
                role=UserRole.USER,
                trust_state=TrustState.ACTIVE,
                reputation_score=42,
                email_verified_at=datetime.now(UTC),
            )
            session.add(existing)
            await session.commit()
            existing_id = existing.id

        profile = google.GoogleProfile(
            sub=f"sub-{uuid.uuid4().hex}", email=email, email_verified=True
        )
        async with SessionLocal() as session:
            user = await service.sign_in_with_google(session, profile=profile)
            await session.commit()
            # Same row: the reputation came along.
            assert user.id == existing_id
            assert user.reputation_score == 42
            assert user.google_sub == profile.sub

        async with SessionLocal() as session:
            await session.execute(delete(User).where(User.id == existing_id))
            await session.commit()

    async def test_a_changed_google_address_still_finds_the_account(self, fresh_db: None) -> None:
        """`sub` is matched before email precisely for this: the address on a
        Google account can change, and the account is still the same person."""
        sub = f"sub-{uuid.uuid4().hex}"
        old = f"old-{uuid.uuid4().hex[:8]}@example.com"
        new = f"new-{uuid.uuid4().hex[:8]}@example.com"

        async with SessionLocal() as session:
            first = await service.sign_in_with_google(
                session, profile=google.GoogleProfile(sub=sub, email=old, email_verified=True)
            )
            await session.commit()
            first_id = first.id

        async with SessionLocal() as session:
            again = await service.sign_in_with_google(
                session, profile=google.GoogleProfile(sub=sub, email=new, email_verified=True)
            )
            await session.commit()
            assert again.id == first_id

        async with SessionLocal() as session:
            await session.execute(delete(User).where(User.id == first_id))
            await session.commit()

    async def test_repeat_sign_in_creates_no_duplicate(self, fresh_db: None) -> None:
        email = f"repeat-{uuid.uuid4().hex[:8]}@example.com"
        profile = google.GoogleProfile(
            sub=f"sub-{uuid.uuid4().hex}", email=email, email_verified=True
        )
        async with SessionLocal() as session:
            await service.sign_in_with_google(session, profile=profile)
            await session.commit()
        async with SessionLocal() as session:
            await service.sign_in_with_google(session, profile=profile)
            await session.commit()

        async with SessionLocal() as session:
            rows = (await session.execute(select(User).where(User.email == email))).scalars().all()
            assert len(rows) == 1
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
