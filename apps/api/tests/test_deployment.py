"""What deploying to a real host must not get wrong.

Three separate hazards, all of which only appear once the app is behind a
proxy on a public domain: a production config that still carries a
development affordance, a rate limiter that believes a caller's claim about
its own address, and a magic link that is reported as sent when it was not.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.api_deps import client_ip
from app.core import email as email_module
from app.core.config import Settings, settings
from app.core.email import EmailDeliveryError, send_email
from app.modules.auth import service as auth_service
from app.shared.errors import EmailDeliveryFailedError
from httpx import AsyncClient
from pydantic import ValidationError
from starlette.requests import Request


def _production(**overrides: Any) -> Settings:
    """A production config with nothing wrong with it, before overrides."""
    base: dict[str, Any] = {
        "app_env": "production",
        "auth_secret": "k" * 48,
        "app_base_url": "https://ghostdodo.com",
        "web_base_url": "https://ghostdodo.com",
        "s3_secret_key": "a-real-secret",
        "email_provider": "resend",
        "resend_api_key": "re_not_a_real_key",
    }
    return Settings(**{**base, **overrides})


class TestProductionHardening:
    def test_a_correct_production_config_boots(self) -> None:
        _production().check_production_hardening()

    def test_console_email_is_refused(self) -> None:
        """A magic link written to the log is a working sign-in for anyone
        who can read the log — the same class of problem as `dev_token`."""
        with pytest.raises(RuntimeError, match="EMAIL_PROVIDER=console"):
            _production(email_provider="console").check_production_hardening()

    def test_a_provider_without_credentials_is_refused(self) -> None:
        """Booting here would mean every sign-in 502s, discovered by users."""
        with pytest.raises(RuntimeError, match="has no API key"):
            _production(resend_api_key="").check_production_hardening()

    def test_plaintext_app_base_url_is_refused(self) -> None:
        """APP_BASE_URL is what the Google callback URL is built from; over
        http it would hand an authorization code to a plaintext hop."""
        with pytest.raises(RuntimeError, match="APP_BASE_URL"):
            _production(app_base_url="http://ghostdodo.com").check_production_hardening()

    def test_the_single_origin_layout_produces_the_registered_callback(self) -> None:
        """The URI registered in the Google console is on the *web* origin,
        because the API is reached through the rewrite. If this string
        changes, sign-in breaks with Google's redirect_uri_mismatch."""
        assert (
            _production().google_callback_url == "https://ghostdodo.com/api/v1/auth/google/callback"
        )

    def test_console_email_is_still_fine_in_development(self) -> None:
        assert Settings(app_env="development").email_configured is True


class TestDatabaseUrl:
    """Managed Postgres providers publish `postgresql://`, and the engine is
    async. Getting this wrong kills the app at import, before any log line
    that would explain why."""

    def test_a_providers_url_is_given_the_async_driver(self) -> None:
        settings_ = Settings(database_url="postgresql://u:p@db.railway.internal:5432/railway")
        assert str(settings_.database_url).startswith("postgresql+asyncpg://")

    def test_the_legacy_postgres_scheme_is_handled_too(self) -> None:
        settings_ = Settings(database_url="postgres://u:p@db.internal:5432/railway")
        assert str(settings_.database_url).startswith("postgresql+asyncpg://")

    def test_the_credentials_and_host_survive_the_rewrite(self) -> None:
        settings_ = Settings(database_url="postgresql://u:p@db.internal:5432/railway")
        url = str(settings_.database_url)
        assert "u:p@db.internal:5432" in url
        assert url.endswith("/railway")

    def test_a_sync_driver_is_refused_rather_than_rewritten(self) -> None:
        """Naming psycopg explicitly is a statement of intent, and it is one
        this engine cannot honour. Say so instead of overriding it."""
        with pytest.raises(ValidationError, match="asyncpg"):
            Settings(database_url="postgresql+psycopg2://u:p@db.internal:5432/railway")


def _request(
    *,
    peer: str = "10.0.0.7",
    forwarded: str | None = None,
    extra: dict[str, str] | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    for name, value in (extra or {}).items():
        headers.append((name.lower().encode(), value.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 40000),
            "scheme": "http",
            "server": ("test", 80),
        }
    )


class TestClientIpBehindProxies:
    """`client_ip` keys rate limits and the stored ip hash. If a caller can
    choose the value, they can pick a fresh bucket per request — or pin the
    blame for their traffic on someone else's address."""

    def test_no_proxies_means_the_header_is_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        assert client_ip(_request(forwarded="1.2.3.4")) == "10.0.0.7"

    def test_the_caller_sits_at_the_configured_offset_from_the_right(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Vercel appended the browser's address, Railway's edge appended
        # Vercel's. Two hops, so the browser is second from the end.
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(_request(forwarded="203.0.113.5, 66.33.60.1")) == "203.0.113.5"

    def test_a_forged_leading_hop_is_not_believed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The old implementation took the leftmost entry, which is exactly
        the one the caller controls."""
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        forwarded = "9.9.9.9, 203.0.113.5, 66.33.60.1"
        assert client_ip(_request(forwarded=forwarded)) == "203.0.113.5"

    def test_a_short_chain_falls_back_to_the_socket_peer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fewer hops than configured means the request did not arrive the
        expected way — a direct hit on the API's own hostname, say."""
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(_request(forwarded="9.9.9.9")) == "10.0.0.7"

    def test_a_missing_header_falls_back_to_the_socket_peer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(_request()) == "10.0.0.7"


_SECRET = "s" * 40


class TestClientIpVouchedByTheWebTier:
    """Production measured on 2026-11-13: Railway's edge replaces
    X-Forwarded-For with Vercel's address, so no hop count finds the
    visitor. The Next proxy names them instead, and the shared secret is
    what makes that header more than something anyone can type."""

    def _vouched(self, ip: str, secret: str = _SECRET, **kw: str) -> Request:
        return _request(
            forwarded="66.33.60.1",
            extra={"X-GD-Client-IP": ip, "X-GD-Proxy-Secret": secret},
            **kw,
        )

    def test_the_web_tier_names_the_visitor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "proxy_shared_secret", _SECRET)
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(self._vouched("203.0.113.5")) == "203.0.113.5"

    def test_a_wrong_secret_is_not_believed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A direct hit on the Railway hostname can send the IP header, so
        without the secret it must fall back as if the header were absent."""
        monkeypatch.setattr(settings, "proxy_shared_secret", _SECRET)
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        assert client_ip(self._vouched("9.9.9.9", secret="guess")) == "10.0.0.7"  # noqa: S106

    def test_the_header_alone_is_not_believed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "proxy_shared_secret", _SECRET)
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        request = _request(extra={"X-GD-Client-IP": "9.9.9.9"})
        assert client_ip(request) == "10.0.0.7"

    def test_no_configured_secret_disables_the_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An empty secret must not match an empty header."""
        monkeypatch.setattr(settings, "proxy_shared_secret", "")
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        assert client_ip(self._vouched("9.9.9.9", secret="")) == "10.0.0.7"

    def test_junk_in_the_ip_header_falls_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "proxy_shared_secret", _SECRET)
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        assert client_ip(self._vouched("not-an-ip")) == "10.0.0.7"

    def test_one_visitor_is_one_bucket_however_spelled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "proxy_shared_secret", _SECRET)
        assert client_ip(self._vouched("2001:DB8:0:0::1")) == "2001:db8::1"

    def test_production_refuses_a_short_secret(self) -> None:
        with pytest.raises(RuntimeError, match="PROXY_SHARED_SECRET"):
            _production(proxy_shared_secret="short").check_production_hardening()  # noqa: S106


class TestMagicLinkDelivery:
    async def test_the_link_points_at_the_route_the_web_app_listens_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`/auth/verify` is a contract with `MagicLinkVerifier`, not a
        detail this module may change."""
        sent: dict[str, str] = {}

        async def capture(**kwargs: str) -> None:
            sent.update(kwargs)

        monkeypatch.setattr(auth_service, "send_email", capture)
        await auth_service.deliver_magic_link("a@example.com", "tok123")

        link = f"{settings.web_base_url}/auth/verify?token=tok123"
        assert link in sent["text"]
        assert link in sent["html"]

    async def test_a_failed_send_is_reported_not_swallowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """202 means "check your mail". It must not be the answer to a mail
        the provider refused."""

        async def refuse(**_: str) -> None:
            raise EmailDeliveryError("nope")

        monkeypatch.setattr(auth_service, "send_email", refuse)
        with pytest.raises(EmailDeliveryFailedError):
            await auth_service.deliver_magic_link("a@example.com", "tok123")

    async def test_sign_in_answers_502_when_the_provider_refuses(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def refuse(**_: str) -> None:
            raise EmailDeliveryError("nope")

        monkeypatch.setattr(auth_service, "send_email", refuse)
        response = await client.post("/api/v1/auth/sign-in", json={"email": "a@example.com"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"


class TestResendProvider:
    async def test_it_sends_what_the_provider_expects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        async def fake_post(_self: Any, url: str, **kwargs: Any) -> httpx.Response:
            captured["url"] = url
            captured.update(kwargs)
            return httpx.Response(200, json={"id": "abc"})

        monkeypatch.setattr(settings, "email_provider", "resend")
        monkeypatch.setattr(settings, "resend_api_key", "re_key")
        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        await send_email(to="a@example.com", subject="s", text="t", html="<p>t</p>")

        assert captured["url"] == email_module.RESEND_ENDPOINT
        assert captured["headers"]["Authorization"] == "Bearer re_key"
        assert captured["json"]["to"] == ["a@example.com"]
        assert captured["json"]["from"] == settings.email_from

    async def test_a_rejection_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def fake_post(_self: Any, _url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(422, json={"message": "domain not verified"})

        monkeypatch.setattr(settings, "email_provider", "resend")
        monkeypatch.setattr(settings, "resend_api_key", "re_key")
        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        with pytest.raises(EmailDeliveryError, match="422"):
            await send_email(to="a@example.com", subject="s", text="t", html="<p>t</p>")

    async def test_a_missing_key_raises_before_any_request(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "email_provider", "resend")
        monkeypatch.setattr(settings, "resend_api_key", "")
        with pytest.raises(EmailDeliveryError, match="RESEND_API_KEY"):
            await send_email(to="a@example.com", subject="s", text="t", html="<p>t</p>")
