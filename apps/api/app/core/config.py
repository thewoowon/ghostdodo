"""Application settings.

Validated at import time so a misconfigured deployment fails at boot rather
than on the first request that happens to touch the bad value.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "test", "staging", "production"]

_INSECURE_SECRET_MARKERS = ("change_me", "changeme", "secret", "dev_only")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "development"
    app_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://ghostdodo:ghostdodo@localhost:5432/ghostdodo")
    )
    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))

    auth_secret: str = "change_me"  # noqa: S105 - dev default; prod rejects it at boot
    session_cookie_name: str = "gd_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 14
    magic_link_ttl_seconds: int = 900

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "auto"
    s3_bucket: str = "ghostdodo-evidence-dev"
    s3_access_key: str = "ghostdodo"
    s3_secret_key: str = "ghostdodo_dev_secret"  # noqa: S105 - local MinIO default
    s3_force_path_style: bool = True
    evidence_upload_url_ttl_seconds: int = 600
    evidence_moderator_url_ttl_seconds: int = 300
    evidence_max_bytes: int = 10 * 1024 * 1024

    # ── Google sign-in ────────────────────────────────────────────
    # Empty until credentials exist. The routes report an unconfigured
    # provider rather than half-starting a flow that cannot complete.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    sentry_dsn: str = ""

    # ── Email ─────────────────────────────────────────────────────
    # "console" logs the magic link instead of sending it. That is a
    # development affordance and an outright token leak anywhere else,
    # so `check_production_hardening` refuses it in production.
    email_provider: Literal["console", "resend"] = "console"
    email_from: str = "GhostDodo <no-reply@ghostdodo.com>"
    resend_api_key: str = ""

    # ── Proxying ──────────────────────────────────────────────────
    # How many proxies sit in front of this app and append to
    # X-Forwarded-For. Every hop beyond this count is caller-supplied and
    # must not be believed. 0 means "trust nothing, use the socket peer".
    #
    # Vercel rewrite -> Railway edge -> app is two hops.
    trusted_proxy_hops: int = 0

    rate_limit_enabled: bool = True

    enable_community: bool = False
    # Jobs are deep links out, not published metrics, so this surface is
    # not held by the launch gate in docs/08 §11.
    enable_jobs: bool = True
    enable_company_portal: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def expose_dev_tokens(self) -> bool:
        """Whether the API may hand a sign-in token back in its own response.

        Development and test only. `is_production` was the wrong gate: it
        leaves staging handing anyone a working session for any address they
        type, which is a full authentication bypass on a deployed host.
        """
        return self.app_env in ("development", "test")

    @property
    def google_auth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def google_callback_url(self) -> str:
        """Must match a redirect URI registered in the Google console exactly,
        including scheme, host, port, and path."""
        return (
            self.google_redirect_uri
            or f"{self.app_base_url.rstrip('/')}/api/v1/auth/google/callback"
        )

    @property
    def email_configured(self) -> bool:
        """Whether a magic link can actually leave the building."""
        if self.email_provider == "console":
            return not self.is_production
        return bool(self.resend_api_key)

    @property
    def cors_origins(self) -> list[str]:
        """Strict CORS: only the known web origin. No wildcards, ever."""
        return [self.web_base_url]

    @field_validator("database_url", mode="before")
    @classmethod
    def _require_async_driver(cls, v: object) -> object:
        """Normalises the URL a managed Postgres hands out.

        Railway (and Heroku, and most others) publish `postgresql://...`.
        SQLAlchemy reads that as "use psycopg2", which is not installed, so
        the app dies at import with a driver error that says nothing about
        the real cause. The scheme is the only difference, so correct it —
        and refuse any *other* driver rather than quietly rewriting it.
        """
        if not isinstance(v, str):
            return v
        scheme, separator, rest = v.partition("://")
        if not separator:
            return v
        if scheme in ("postgres", "postgresql"):
            return f"postgresql+asyncpg://{rest}"
        if scheme != "postgresql+asyncpg":
            raise ValueError(
                f"DATABASE_URL must use the asyncpg driver, got '{scheme}'. "
                "The engine is async; a sync driver cannot serve it."
            )
        return v

    @field_validator("auth_secret")
    @classmethod
    def _require_secret(cls, v: str) -> str:
        # Env-specific strength rules live in `check_production_hardening`;
        # an empty secret is wrong in every environment.
        if not v.strip():
            raise ValueError("AUTH_SECRET must be set")
        return v

    def check_production_hardening(self) -> None:
        """Called from the app lifespan. Refuses to serve production traffic
        with development placeholders still in place."""
        if not self.is_production:
            return
        problems: list[str] = []
        lowered = self.auth_secret.lower()
        if len(self.auth_secret) < 32 or any(m in lowered for m in _INSECURE_SECRET_MARKERS):
            problems.append("AUTH_SECRET is a placeholder or too short (need >=32 random chars)")
        if self.expose_dev_tokens:
            problems.append("dev sign-in tokens must never be exposed in production")
        if "change_me" in self.s3_secret_key.lower():
            problems.append("S3_SECRET_KEY is a placeholder")
        if self.web_base_url.startswith("http://"):
            problems.append("WEB_BASE_URL must be https in production")
        if self.app_base_url.startswith("http://"):
            problems.append("APP_BASE_URL must be https in production")
        if self.email_provider == "console":
            # Console delivery writes a working sign-in token to the log.
            problems.append("EMAIL_PROVIDER=console leaks sign-in tokens to logs")
        elif not self.email_configured:
            problems.append(f"EMAIL_PROVIDER={self.email_provider} has no API key")
        if problems:
            raise RuntimeError("Refusing to start in production: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
