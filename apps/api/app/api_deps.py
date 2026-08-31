"""Shared FastAPI dependencies: session, current user, role gates."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import read_session
from app.db.session import get_db
from app.modules.users.models import User
from app.shared.enums import TrustState, UserRole
from app.shared.errors import ForbiddenError, UnauthorizedError

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_optional(request: Request, db: DbSession) -> User | None:
    cookie = request.cookies.get(settings.session_cookie_name)
    user_id = await read_session(cookie)
    if user_id is None:
        return None
    return await db.get(User, user_id)


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise UnauthorizedError()
    if user.deactivated_at is not None:
        raise ForbiddenError("비활성화된 계정입니다.")
    return user


async def get_contributing_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """A suspended account can still read; it cannot add to the archive."""
    if user.trust_state is TrustState.SUSPENDED:
        raise ForbiddenError("현재 계정으로는 기록을 등록할 수 없습니다.")
    return user


async def get_moderator(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role not in (UserRole.MODERATOR, UserRole.ADMIN):
        raise ForbiddenError()
    return user


async def get_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role is not UserRole.ADMIN:
        raise ForbiddenError()
    return user


def client_ip(request: Request) -> str | None:
    """Trusts the leftmost X-Forwarded-For hop. Behind a proxy that appends
    rather than replaces, configure the proxy to strip inbound values."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
ContributingUser = Annotated[User, Depends(get_contributing_user)]
Moderator = Annotated[User, Depends(get_moderator)]
Admin = Annotated[User, Depends(get_admin)]
