"""Reputation and Dodo Credit ledgers.

Two invariants hold everywhere in this module:

  1. Ledgers are append-only. A reversal is a new negative row that points at
     the row it undoes; nothing is ever edited or deleted.
  2. Awards are for completeness, evidence, and corroboration — never for
     reporting something negative. Every award below is keyed on the quality
     of the contribution, and the same amounts apply whether the company
     answered promptly or not at all (docs/07 §2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reputation.models import CreditLedger, ReputationEvent
from app.modules.users.models import User
from app.shared.enums import CreditEventType, ReputationEventType, ReputationRank


@dataclass(frozen=True, slots=True)
class Award:
    reputation: int
    credits: int


# Identical regardless of what the company did. A verified "they replied in
# three days" is worth exactly as much as a verified silence.
AWARDS: dict[ReputationEventType, Award] = {
    ReputationEventType.REPORT_SUBMITTED_COMPLETE: Award(reputation=5, credits=5),
    ReputationEventType.REPORT_VERIFIED: Award(reputation=20, credits=20),
    ReputationEventType.EVIDENCE_VERIFIED: Award(reputation=15, credits=10),
    ReputationEventType.REPORT_CORROBORATED: Award(reputation=10, credits=5),
    ReputationEventType.FACTUAL_CORRECTION_ACCEPTED: Award(reputation=25, credits=15),
    ReputationEventType.COMPANY_METADATA_ACCEPTED: Award(reputation=8, credits=5),
    ReputationEventType.PII_FLAG_ACCEPTED: Award(reputation=15, credits=10),
    ReputationEventType.HELPFUL_COMMUNITY_ANSWER: Award(reputation=3, credits=2),
    ReputationEventType.REPORT_REVERSED: Award(reputation=-25, credits=0),
    ReputationEventType.MODERATION_SANCTION: Award(reputation=-50, credits=0),
}

# Higher tiers need demonstrated accuracy, not just volume: points alone must
# not buy standing (docs/07 §3).
RANK_THRESHOLDS: tuple[tuple[ReputationRank, int, int], ...] = (
    (ReputationRank.DODO_RANGER, 2000, 60),
    (ReputationRank.ARCHIVIST, 1000, 30),
    (ReputationRank.VERIFIER, 400, 12),
    (ReputationRank.RECORDER, 150, 4),
    (ReputationRank.EXPLORER, 40, 1),
    (ReputationRank.OBSERVER, 0, 0),
)

# Above this share of reversed contributions, higher ranks are withheld
# regardless of score.
MAX_REVERSAL_RATIO_FOR_TRUSTED_RANK = 0.2
_TRUSTED_RANKS = frozenset(
    {ReputationRank.VERIFIER, ReputationRank.ARCHIVIST, ReputationRank.DODO_RANGER}
)


def rank_for(user: User) -> ReputationRank:
    total = user.verified_contribution_count + user.reversed_contribution_count
    reversal_ratio = (user.reversed_contribution_count / total) if total else 0.0

    for rank, min_score, min_verified in RANK_THRESHOLDS:
        if user.reputation_score < min_score or user.verified_contribution_count < min_verified:
            continue
        if rank in _TRUSTED_RANKS and reversal_ratio > MAX_REVERSAL_RATIO_FOR_TRUSTED_RANK:
            continue
        return rank
    return ReputationRank.OBSERVER


async def award(
    session: AsyncSession,
    *,
    user: User,
    event_type: ReputationEventType,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    dedupe_key: str | None = None,
    detail: dict[str, object] | None = None,
) -> ReputationEvent | None:
    """Append a reputation event and its matching credit entry.

    Returns None when `dedupe_key` has already been awarded — verifying the
    same report twice must not pay twice. The caller's transaction is not
    rolled back on that path.
    """
    if dedupe_key:
        already = (
            await session.execute(
                select(ReputationEvent.id).where(ReputationEvent.dedupe_key == dedupe_key)
            )
        ).first()
        if already is not None:
            return None

    amounts = AWARDS[event_type]

    user.reputation_score = max(0, user.reputation_score + amounts.reputation)
    event = ReputationEvent(
        user_id=user.id,
        event_type=event_type,
        delta=amounts.reputation,
        balance_after=user.reputation_score,
        subject_type=subject_type,
        subject_id=subject_id,
        dedupe_key=dedupe_key,
        detail=detail or {},
    )
    session.add(event)

    if amounts.credits:
        user.credit_balance = max(0, user.credit_balance + amounts.credits)
        session.add(
            CreditLedger(
                user_id=user.id,
                event_type=_credit_type_for(event_type),
                delta=amounts.credits,
                balance_after=user.credit_balance,
                subject_type=subject_type,
                subject_id=subject_id,
                dedupe_key=f"credit:{dedupe_key}" if dedupe_key else None,
            )
        )

    user.rank = rank_for(user)

    try:
        await session.flush()
    except IntegrityError:
        # Lost a race against a concurrent award of the same dedupe key.
        await session.rollback()
        return None
    return event


def _credit_type_for(event_type: ReputationEventType) -> CreditEventType:
    if event_type is ReputationEventType.REPORT_VERIFIED:
        return CreditEventType.VERIFICATION_BONUS
    if event_type in (
        ReputationEventType.REPORT_REVERSED,
        ReputationEventType.MODERATION_SANCTION,
    ):
        return CreditEventType.REVERSAL
    return CreditEventType.CONTRIBUTION_REWARD


async def reverse(
    session: AsyncSession,
    *,
    user: User,
    original_event_id: uuid.UUID,
    reason: str,
) -> ReputationEvent | None:
    """Record a reversal when a verified contribution is later overturned."""
    user.reversed_contribution_count += 1
    user.verified_contribution_count = max(0, user.verified_contribution_count - 1)
    event = await award(
        session,
        user=user,
        event_type=ReputationEventType.REPORT_REVERSED,
        subject_type="reputation_event",
        subject_id=original_event_id,
        dedupe_key=f"reversal:{original_event_id}",
        detail={"reason": reason},
    )
    if event is not None:
        event.reverses_event_id = original_event_id
    # Standing is recomputed after the counters change, so a reversal can
    # demote as well as deduct.
    user.rank = rank_for(user)
    await session.flush()
    return event
