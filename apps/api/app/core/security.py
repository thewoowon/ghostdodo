"""Sessions, tokens, and hashing.

Sessions are signed, httponly cookies holding an opaque session id; the
session record lives in Redis so a sign-out or a sanction takes effect
immediately rather than waiting for a JWT to expire.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Final

from itsdangerous import BadSignature, URLSafeSerializer

from app.core.config import settings
from app.core.redis import get_redis

_SESSION_SALT: Final = "ghostdodo.session.v1"
_SESSION_PREFIX: Final = "session:"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(settings.auth_secret, salt=_SESSION_SALT)


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Tokens are stored hashed so a database read cannot be replayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def hash_ip(ip: str | None) -> str | None:
    """Salted hash for abuse signals. Raw IPs are never persisted — data
    minimization under PIPA (docs/08 §9)."""
    if not ip:
        return None
    return hmac.new(settings.auth_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


async def create_session(user_id: uuid.UUID) -> str:
    """Returns the signed cookie value."""
    session_id = str(uuid.uuid4())
    redis = get_redis()
    await redis.set(
        f"{_SESSION_PREFIX}{session_id}",
        str(user_id),
        ex=settings.session_ttl_seconds,
    )
    return str(_serializer().dumps({"sid": session_id}))


async def read_session(cookie_value: str | None) -> uuid.UUID | None:
    if not cookie_value:
        return None
    try:
        payload = _serializer().loads(cookie_value)
    except BadSignature:
        return None
    session_id = payload.get("sid") if isinstance(payload, dict) else None
    if not session_id:
        return None
    raw = await get_redis().get(f"{_SESSION_PREFIX}{session_id}")
    if raw is None:
        return None
    try:
        # The client is created with decode_responses=True, so this is str.
        return uuid.UUID(str(raw))
    except ValueError:
        return None


async def destroy_session(cookie_value: str | None) -> None:
    if not cookie_value:
        return
    try:
        payload = _serializer().loads(cookie_value)
    except BadSignature:
        return
    session_id = payload.get("sid") if isinstance(payload, dict) else None
    if session_id:
        await get_redis().delete(f"{_SESSION_PREFIX}{session_id}")


def magic_link_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.magic_link_ttl_seconds)
