"""Google sign-in — server-side authorization code flow.

The browser never handles a token. Google redirects back to the API, the API
exchanges the code using the client secret, and the result is the same
httponly session cookie the magic link issues. That keeps one session
mechanism in the system rather than two.

`state` is minted here and held in Redis, so a callback that did not begin
with a request from this server is rejected before any code is exchanged.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import new_token
from app.shared.errors import AuthProviderError, AuthProviderUnavailableError

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"  # noqa: S105 - a URL, not a secret

_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
_SCOPES = "openid email profile"

_STATE_PREFIX = "oauth:google:state:"
STATE_TTL_SECONDS = 600
"""Long enough to pick an account and type a password, short enough that a
leaked authorize URL is not a standing invitation."""

DEFAULT_NEXT = "/"


@dataclass(frozen=True, slots=True)
class GoogleProfile:
    """Only what an account needs. No avatar, no locale, no given/family
    split — the product's public identity is a pseudonymous handle."""

    sub: str
    email: str
    email_verified: bool


def safe_next_path(raw: str | None) -> str:
    """Where to land after signing in.

    Only a rooted same-site path survives. The callback redirects to whatever
    this returns, so anything else would make sign-in an open redirect — and
    an open redirect on an auth callback is a phishing primitive.
    """
    if not raw:
        return DEFAULT_NEXT
    path = raw.strip()
    if not path.startswith("/") or path.startswith("//"):
        return DEFAULT_NEXT
    return path


def require_configured() -> None:
    if not settings.google_auth_configured:
        raise AuthProviderUnavailableError()


async def start(next_path: str | None) -> str:
    """Mints state and returns the URL to send the browser to."""
    require_configured()
    state = new_token(24)
    await get_redis().set(
        f"{_STATE_PREFIX}{state}", safe_next_path(next_path), ex=STATE_TTL_SECONDS
    )
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_callback_url,
        "response_type": "code",
        "scope": _SCOPES,
        "state": state,
        # Ask for an account choice every time: a shared machine must not
        # sign someone in as the previous person without a prompt.
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def consume_state(state: str | None) -> str:
    """Validates and burns the state, returning where to land afterwards."""
    if not state:
        raise AuthProviderError()
    key = f"{_STATE_PREFIX}{state}"
    redis = get_redis()
    stored = await redis.get(key)
    if stored is None:
        raise AuthProviderError()
    await redis.delete(key)
    # decode_responses=True, so this is str; the client's type says otherwise.
    return safe_next_path(stored if isinstance(stored, str) else stored.decode())


def _decode_id_token_claims(id_token: str) -> dict[str, Any]:
    """Reads the payload of an id_token received *directly from Google's
    token endpoint*.

    The signature is not re-verified, and that is deliberate rather than an
    omission: this token arrived over a TLS connection to Google, in response
    to a request authenticated with our client secret, so there is no
    untrusted party in the path. Google documents this exact allowance for
    the authorization code flow. The claims below are still checked — a
    token that is genuinely Google's can still be one issued for a different
    application.

    An id_token that reached us any other way (a browser, a redirect
    fragment) must NOT be read with this function.
    """
    parts = id_token.split(".")
    if len(parts) != 3:
        raise AuthProviderError()
    payload = parts[1]
    try:
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthProviderError() from exc
    if not isinstance(claims, dict):
        raise AuthProviderError()
    return claims


def _validate_claims(claims: dict[str, Any]) -> GoogleProfile:
    if claims.get("iss") not in _ISSUERS:
        raise AuthProviderError()
    # A token minted for another client id is not ours to accept.
    if claims.get("aud") != settings.google_client_id:
        raise AuthProviderError()

    expires_at = claims.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(datetime.now(UTC).timestamp()):
        raise AuthProviderError()

    sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(sub, str) or not sub or not isinstance(email, str) or not email:
        raise AuthProviderError()

    # Google sets this false for an address the account has not proven it
    # owns. Trusting it anyway would let one account claim another's email.
    if claims.get("email_verified") is not True:
        raise AuthProviderError("이메일이 확인되지 않은 구글 계정입니다.")

    return GoogleProfile(sub=sub, email=email.lower().strip(), email_verified=True)


async def exchange_code(code: str) -> GoogleProfile:
    """Trades the one-time code for the signed-in identity."""
    require_configured()
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(
                TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_callback_url,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise AuthProviderError("구글에 연결하지 못했습니다.") from exc

    if response.status_code != 200:
        raise AuthProviderError()

    body = response.json()
    id_token = body.get("id_token")
    if not isinstance(id_token, str):
        raise AuthProviderError()

    return _validate_claims(_decode_id_token_claims(id_token))
