from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.api_deps import CurrentUser, DbSession, client_ip
from app.core import rate_limit
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_session, destroy_session, hash_ip
from app.modules.auth import google, service
from app.shared.errors import AppError

log = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignInRequest(BaseModel):
    email: EmailStr


class SignInAccepted(BaseModel):
    message: str = "로그인 링크를 이메일로 보냈습니다."
    # Populated in development and test only, so a local setup needs no mail
    # server. Never on a deployed environment.
    dev_token: str | None = None


class VerifyRequest(BaseModel):
    token: str


class AuthProviders(BaseModel):
    """What the client may offer. The web app renders the Google button from
    this rather than from its own env, so a misconfigured API cannot produce
    a button that leads nowhere."""

    google: bool
    magic_link: bool = True


class SessionUser(BaseModel):
    id: str
    handle: str
    role: str
    reputation_score: int
    credit_balance: int
    rank: str


def _set_session_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        value,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        # Lax still sends the cookie on top-level navigation from an email
        # link, while blocking it on cross-site POSTs.
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


@router.get("/providers", response_model=AuthProviders)
async def providers() -> AuthProviders:
    return AuthProviders(google=settings.google_auth_configured)


@router.get("/google/start")
async def google_start(
    # Aliased because the query parameter really is `next`, while the name
    # `next` would shadow the builtin.
    next_path: Annotated[str | None, Query(alias="next", max_length=300)] = None,
) -> RedirectResponse:
    """Sends the browser to Google. `next` is where to land afterwards, and
    is reduced to a same-site path before it is stored."""
    url = await google.start(next_path)
    return RedirectResponse(url, status_code=302)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: DbSession,
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=200)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
) -> RedirectResponse:
    """Google's return leg.

    Ends in a redirect either way — this URL is reached by a browser
    navigation, not by fetch, so an error envelope would leave the user
    staring at raw JSON. Failures land on the sign-in page with a reason.
    """
    web = settings.web_base_url.rstrip("/")

    # The state is burned first, before the code is worth anything, so a
    # replayed callback cannot mint a second session.
    try:
        next_path = await google.consume_state(state)
    except AppError:
        return RedirectResponse(f"{web}/sign-in?error=state", status_code=302)

    # The user pressed cancel on Google's consent screen.
    if error or not code:
        return RedirectResponse(f"{web}/sign-in?error=cancelled", status_code=302)

    try:
        profile = await google.exchange_code(code)
        user = await service.sign_in_with_google(db, profile=profile)
        await db.commit()
    except AppError:
        return RedirectResponse(f"{web}/sign-in?error=google", status_code=302)

    if user.deactivated_at is not None:
        return RedirectResponse(f"{web}/sign-in?error=deactivated", status_code=302)

    response = RedirectResponse(f"{web}{next_path}", status_code=302)
    _set_session_cookie(response, await create_session(user.id))
    log.info("auth.google.callback", ip_hash=hash_ip(client_ip(request)))
    return response


@router.post("/sign-in", response_model=SignInAccepted, status_code=202)
async def sign_in(payload: SignInRequest, request: Request, db: DbSession) -> SignInAccepted:
    ip_hash = hash_ip(client_ip(request))
    await rate_limit.enforce("sign_in", ip_hash or "anon", rate_limit.SIGN_IN_REQUEST)

    token = await service.request_magic_link(db, email=payload.email, ip_hash=ip_hash)
    await db.commit()
    await service.deliver_magic_link(payload.email, token)

    # The response is identical whether or not the address has an account —
    # sign-in must not double as an account-existence oracle.
    #
    # The token itself comes back only in development and test, where there
    # is no mail server. On any deployed environment — staging included —
    # returning it would be an authentication bypass for any address a
    # caller cares to type.
    return SignInAccepted(dev_token=token if settings.expose_dev_tokens else None)


@router.post("/verify", response_model=SessionUser)
async def verify(payload: VerifyRequest, response: Response, db: DbSession) -> SessionUser:
    user = await service.consume_magic_link(db, token=payload.token)
    await db.commit()
    cookie = await create_session(user.id)
    _set_session_cookie(response, cookie)
    return SessionUser(
        id=str(user.id),
        handle=user.handle,
        role=user.role.value,
        reputation_score=user.reputation_score,
        credit_balance=user.credit_balance,
        rank=user.rank.value,
    )


@router.post("/sign-out", status_code=204)
async def sign_out(request: Request, response: Response) -> None:
    await destroy_session(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=SessionUser)
async def me(user: CurrentUser) -> SessionUser:
    return SessionUser(
        id=str(user.id),
        handle=user.handle,
        role=user.role.value,
        reputation_score=user.reputation_score,
        credit_balance=user.credit_balance,
        rank=user.rank.value,
    )
