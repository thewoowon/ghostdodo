"""Passwordless sign-in: Google, and the original magic link.

Neither stores a password — one less category of breach. The two providers
are deliberately not separate account systems: both resolve to one `User`
row keyed on a verified email, so a contributor who signs in with Google
after using the magic link keeps their reports, reputation, and handle.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import EmailDeliveryError, send_email
from app.core.logging import get_logger
from app.core.security import hash_token, magic_link_expiry, new_token
from app.modules.auth.google import GoogleProfile
from app.modules.users.models import MagicLinkToken, User
from app.shared.enums import TrustState, UserRole
from app.shared.errors import EmailDeliveryFailedError, UnauthorizedError

log = get_logger(__name__)

_HANDLE_SAFE = re.compile(r"[^a-z0-9]+")


def _handle_from_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    base = _HANDLE_SAFE.sub("", local)[:16] or "dodo"
    # Random suffix: a handle is a public pseudonym and must not be a
    # guessable transform of the user's email address.
    return f"{base}_{secrets.token_hex(3)}"


async def request_magic_link(session: AsyncSession, *, email: str, ip_hash: str | None) -> str:
    """Creates a single-use token. Returns the raw token for delivery; only
    its hash is persisted."""
    token = new_token()
    record = MagicLinkToken(
        email=email.lower().strip(),
        token_hash=hash_token(token),
        expires_at=magic_link_expiry(),
        created_at=datetime.now(UTC),
        requested_ip_hash=ip_hash,
    )
    session.add(record)
    await session.flush()
    return token


async def consume_magic_link(session: AsyncSession, *, token: str) -> User:
    """Validates and burns the token, creating the user on first sign-in."""
    token_hash = hash_token(token)
    record = (
        await session.execute(select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash))
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if record is None or record.consumed_at is not None or record.expires_at < now:
        # One message for every failure mode, so a probe cannot distinguish
        # "no such token" from "already used".
        raise UnauthorizedError("링크가 만료되었거나 이미 사용되었습니다.")

    record.consumed_at = now

    user = (
        await session.execute(select(User).where(User.email == record.email))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=record.email,
            handle=_handle_from_email(record.email),
            role=UserRole.USER,
            trust_state=TrustState.NEW,
            email_verified_at=now,
        )
        session.add(user)
        await session.flush()
    elif user.email_verified_at is None:
        user.email_verified_at = now

    return user


_MAGIC_LINK_SUBJECT = "GhostDodo 로그인 링크"


def _magic_link_body(link: str) -> tuple[str, str]:
    """Plain text and HTML for the same message.

    The path is `/auth/verify` because that is what `MagicLinkVerifier`
    listens on — the emailed link is part of the web app's route contract,
    not a detail this module is free to change.
    """
    minutes = max(1, settings.magic_link_ttl_seconds // 60)
    text = (
        "아래 주소로 로그인하세요.\n\n"
        f"{link}\n\n"
        f"이 링크는 {minutes}분 뒤 만료되며 한 번만 사용할 수 있습니다.\n"
        "요청한 적이 없다면 이 메일은 무시하셔도 됩니다."
    )
    safe = escape(link, quote=True)
    html = (
        '<div style="font-family:system-ui,-apple-system,sans-serif;'
        'font-size:15px;line-height:1.7;color:#1a1a1a">'
        "<p>아래 주소로 로그인하세요.</p>"
        f'<p><a href="{safe}">{safe}</a></p>'
        f"<p>이 링크는 {minutes}분 뒤 만료되며 한 번만 사용할 수 있습니다.<br>"
        "요청한 적이 없다면 이 메일은 무시하셔도 됩니다.</p>"
        "</div>"
    )
    return text, html


async def deliver_magic_link(email: str, token: str) -> None:
    """Sends the sign-in link through whichever provider is configured.

    A delivery failure is raised, not logged and swallowed: the caller
    answers 202 ("check your mail"), and that answer must not be given for a
    mail that was never accepted.
    """
    link = f"{settings.web_base_url}/auth/verify?token={token}"
    text, html = _magic_link_body(link)
    try:
        await send_email(to=email, subject=_MAGIC_LINK_SUBJECT, text=text, html=html)
    except EmailDeliveryError as exc:
        # The address never reaches the log line — a failed send is not a
        # reason to write down who was trying to sign in.
        log.warning("auth.magic_link.undelivered", reason=str(exc))
        raise EmailDeliveryFailedError from exc


async def sign_in_with_google(session: AsyncSession, *, profile: GoogleProfile) -> User:
    """Resolves a verified Google identity to an account, creating one on
    first sign-in.

    Match order matters. `sub` comes first because it is stable for the life
    of the Google account, while the address on it can be changed or
    released; matching on email alone would hand an account to whoever
    inherits an old address. Email is the second key precisely so that a
    contributor who started with the magic link lands on the same row rather
    than a duplicate — and it is only trusted here because the caller has
    already rejected any profile Google did not mark verified.
    """
    now = datetime.now(UTC)

    user = (
        await session.execute(select(User).where(User.google_sub == profile.sub))
    ).scalar_one_or_none()

    if user is None:
        user = (
            await session.execute(select(User).where(User.email == profile.email))
        ).scalar_one_or_none()
        if user is not None:
            # Linking an existing magic-link account to its Google identity.
            user.google_sub = profile.sub

    if user is None:
        user = User(
            email=profile.email,
            handle=_handle_from_email(profile.email),
            google_sub=profile.sub,
            role=UserRole.USER,
            trust_state=TrustState.NEW,
            email_verified_at=now,
        )
        session.add(user)
        await session.flush()
    elif user.email_verified_at is None:
        user.email_verified_at = now

    log.info("auth.google.signed_in", user_id=str(user.id))
    return user
