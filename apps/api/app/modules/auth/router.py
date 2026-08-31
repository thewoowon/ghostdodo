from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, EmailStr

from app.api_deps import CurrentUser, DbSession, client_ip
from app.core import rate_limit
from app.core.config import settings
from app.core.security import create_session, destroy_session, hash_ip
from app.modules.auth import service

router = APIRouter(prefix="/auth", tags=["auth"])


class SignInRequest(BaseModel):
    email: EmailStr


class SignInAccepted(BaseModel):
    message: str = "로그인 링크를 이메일로 보냈습니다."
    # Populated only outside production, so local development does not need
    # a mail server.
    dev_token: str | None = None


class VerifyRequest(BaseModel):
    token: str


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


@router.post("/sign-in", response_model=SignInAccepted, status_code=202)
async def sign_in(payload: SignInRequest, request: Request, db: DbSession) -> SignInAccepted:
    ip_hash = hash_ip(client_ip(request))
    await rate_limit.enforce("sign_in", ip_hash or "anon", rate_limit.SIGN_IN_REQUEST)

    token = await service.request_magic_link(db, email=payload.email, ip_hash=ip_hash)
    await db.commit()
    await service.deliver_magic_link(payload.email, token)

    # The response is identical whether or not the address has an account —
    # sign-in must not double as an account-existence oracle.
    return SignInAccepted(dev_token=None if settings.is_production else token)


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
