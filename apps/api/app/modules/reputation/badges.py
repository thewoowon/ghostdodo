"""Badges.

The table and the profile read have existed since the schema landed; nothing
ever wrote a row. These rules fill that gap.

Two things shape the set deliberately:

* Every rule keys on *verified contribution*, never on what a contribution
  said. There is no badge for reporting silence, for accusing many
  companies, or for volume of negative findings — the same rule that governs
  the award table one module over (docs/07 §2).
* No streaks. docs/07 §4 lists a consecutive-days badge and warns against
  addictive dark patterns in the same breath; a badge that punishes taking a
  week off is exactly that, so it is left unbuilt rather than built carefully.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reputation.models import ReputationEvent, UserBadge
from app.modules.users.models import User
from app.shared.enums import ReputationEventType


@dataclass(frozen=True, slots=True)
class BadgeRule:
    code: str
    label: str
    description: str
    #: Verified contributions required, or None when the rule keys on events.
    min_verified: int | None = None
    #: Accepted events of this type required.
    event_type: ReputationEventType | None = None
    min_events: int = 1


BADGE_RULES: tuple[BadgeRule, ...] = (
    BadgeRule(
        code="FIRST_RECORD",
        label="첫 기록",
        description="검증을 마친 첫 기록을 남겼습니다.",
        min_verified=1,
    ),
    BadgeRule(
        code="VERIFIED_10",
        label="검증된 기록 10회",
        description="검증을 마친 기록이 10건 쌓였습니다.",
        min_verified=10,
    ),
    BadgeRule(
        code="VERIFIED_50",
        label="검증된 기록 50회",
        description="검증을 마친 기록이 50건 쌓였습니다.",
        min_verified=50,
    ),
    BadgeRule(
        code="CORRECTION_CONTRIBUTOR",
        label="정정 기여",
        description="사실관계 정정이 받아들여졌습니다.",
        event_type=ReputationEventType.FACTUAL_CORRECTION_ACCEPTED,
    ),
    BadgeRule(
        code="FACT_CHECKER",
        label="팩트체커",
        description="개인 신상 정보 신고가 받아들여졌습니다.",
        event_type=ReputationEventType.PII_FLAG_ACCEPTED,
    ),
)

_RULES_BY_CODE = {rule.code: rule for rule in BADGE_RULES}


def rule_for(code: str) -> BadgeRule | None:
    return _RULES_BY_CODE.get(code)


async def _event_count(
    session: AsyncSession, *, user_id: uuid.UUID, event_type: ReputationEventType
) -> int:
    return (
        await session.execute(
            select(func.count(ReputationEvent.id)).where(
                ReputationEvent.user_id == user_id,
                ReputationEvent.event_type == event_type,
            )
        )
    ).scalar_one()


async def _earned(session: AsyncSession, *, user: User, rule: BadgeRule) -> bool:
    if rule.min_verified is not None:
        return user.verified_contribution_count >= rule.min_verified
    if rule.event_type is not None:
        count = await _event_count(session, user_id=user.id, event_type=rule.event_type)
        return count >= rule.min_events
    return False


async def evaluate(session: AsyncSession, *, user: User) -> list[str]:
    """Grants any newly earned badge. Returns the codes granted this call.

    Runs inside the caller's transaction, alongside the ledger rows that
    caused it, so a badge cannot survive a rolled-back award.

    Badges are not revoked here. A reversal already deducts reputation and
    can demote a rank; also clawing back "첫 기록" would be a third punishment
    for one mistake, and the ledger remains the auditable record either way.
    """
    held = set(
        (
            await session.execute(
                select(UserBadge.badge_code).where(
                    UserBadge.user_id == user.id, UserBadge.revoked_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )

    granted: list[str] = []
    for rule in BADGE_RULES:
        if rule.code in held:
            continue
        if await _earned(session, user=user, rule=rule):
            session.add(UserBadge(user_id=user.id, badge_code=rule.code))
            granted.append(rule.code)

    if granted:
        # Sessions are autoflush=False; without this the badge just added is
        # invisible to the `held` query on the next call in the same
        # transaction, and a duplicate hits the unique constraint.
        await session.flush()
    return granted


def labels(codes: Sequence[str]) -> list[BadgeRule]:
    """Known badges only, in the canonical order rather than award order, so
    a profile does not reshuffle as badges arrive."""
    held = set(codes)
    return [rule for rule in BADGE_RULES if rule.code in held]
