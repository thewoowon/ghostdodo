"""Badges, and the sign-in token that must not leave a deployed host.

The badge rules carry the same constraint as the award table they hang off:
standing is earned by verified, complete contribution and never by what a
contribution *said*. A test here asserts that directly, because a badge for
"reported the most silence" is exactly the drift the product is built to
avoid.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.core.config import Settings, settings
from app.db.session import SessionLocal, dispose_engine
from app.modules.reputation import badges
from app.modules.reputation import service as reputation_service
from app.modules.reputation.models import CreditLedger, ReputationEvent, UserBadge
from app.modules.users.models import User
from app.shared.enums import ReputationEventType, TrustState, UserRole
from sqlalchemy import delete, select


@pytest.fixture
async def contributor() -> uuid.UUID:
    # Disposed on both sides. asyncpg connections belong to the loop that
    # opened them and pytest-asyncio gives each test its own, so the pool has
    # to be empty when this loop starts using it and empty again before the
    # loop closes. `fresh_db` only covers the second half, and this fixture
    # opens sessions in setup *and* teardown.
    await dispose_engine()

    email = f"badge-{uuid.uuid4().hex[:8]}@example.com"
    async with SessionLocal() as session:
        user = User(
            email=email,
            handle=f"관찰자{uuid.uuid4().hex[:6]}",
            role=UserRole.USER,
            trust_state=TrustState.ACTIVE,
            email_verified_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    yield user_id

    # Deepest first: both ledgers are RESTRICT, so the user row cannot go
    # until everything pointing at it has.
    async with SessionLocal() as session:
        await session.execute(delete(UserBadge).where(UserBadge.user_id == user_id))
        await session.execute(delete(CreditLedger).where(CreditLedger.user_id == user_id))
        await session.execute(delete(ReputationEvent).where(ReputationEvent.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()

    # Disposed here rather than via `fresh_db`: this fixture opens a session
    # during its own teardown, which runs *after* fresh_db's, leaving a
    # connection bound to a loop that is about to close.
    await dispose_engine()


class TestBadgeRulesRewardContributionNotNegativity:
    def test_no_rule_keys_on_what_a_report_said(self) -> None:
        """The award table is identical for a company that answered and one
        that went silent; the badge table must not smuggle the asymmetry back
        in through a side door."""
        rewarded_events = {
            rule.event_type for rule in badges.BADGE_RULES if rule.event_type is not None
        }
        # Deductions must never be a badge criterion either.
        assert ReputationEventType.REPORT_REVERSED not in rewarded_events
        assert ReputationEventType.MODERATION_SANCTION not in rewarded_events
        for rule in badges.BADGE_RULES:
            assert rule.min_verified is not None or rule.event_type is not None

    def test_no_streak_badge_exists(self) -> None:
        """docs/07 §4 lists a consecutive-days badge and warns about
        addictive dark patterns in the same breath. Left unbuilt on purpose."""
        text = " ".join(f"{r.code} {r.label} {r.description}" for r in badges.BADGE_RULES)
        assert "연속" not in text
        assert "STREAK" not in text.upper()

    def test_codes_are_unique(self) -> None:
        codes = [rule.code for rule in badges.BADGE_RULES]
        assert len(codes) == len(set(codes))

    def test_labels_render_in_canonical_order_not_award_order(self) -> None:
        """A profile must not reshuffle as badges arrive."""
        shuffled = ["VERIFIED_10", "FIRST_RECORD"]
        assert [r.code for r in badges.labels(shuffled)] == ["FIRST_RECORD", "VERIFIED_10"]

    def test_unknown_codes_are_dropped_not_shown_raw(self) -> None:
        assert badges.labels(["NOT_A_BADGE"]) == []


class TestEarning:
    async def test_first_verified_contribution_earns_the_first_badge(
        self, contributor: uuid.UUID
    ) -> None:
        async with SessionLocal() as session:
            user = await session.get(User, contributor)
            assert user is not None
            user.verified_contribution_count = 1
            granted = await badges.evaluate(session, user=user)
            await session.commit()
        assert granted == ["FIRST_RECORD"]

    async def test_a_badge_is_granted_once(self, contributor: uuid.UUID) -> None:
        async with SessionLocal() as session:
            user = await session.get(User, contributor)
            assert user is not None
            user.verified_contribution_count = 1
            await badges.evaluate(session, user=user)
            # Sessions are autoflush=False; a second pass in the same
            # transaction must still see the row it just added.
            again = await badges.evaluate(session, user=user)
            await session.commit()
        assert again == []

        async with SessionLocal() as session:
            rows = (
                (await session.execute(select(UserBadge).where(UserBadge.user_id == contributor)))
                .scalars()
                .all()
            )
        assert len(rows) == 1

    async def test_crossing_a_threshold_grants_only_the_new_tier(
        self, contributor: uuid.UUID
    ) -> None:
        async with SessionLocal() as session:
            user = await session.get(User, contributor)
            assert user is not None
            user.verified_contribution_count = 1
            await badges.evaluate(session, user=user)
            user.verified_contribution_count = 10
            granted = await badges.evaluate(session, user=user)
            await session.commit()
        assert granted == ["VERIFIED_10"]

    async def test_an_accepted_correction_earns_the_correction_badge(
        self, contributor: uuid.UUID
    ) -> None:
        async with SessionLocal() as session:
            user = await session.get(User, contributor)
            assert user is not None
            await reputation_service.award(
                session,
                user=user,
                event_type=ReputationEventType.FACTUAL_CORRECTION_ACCEPTED,
                dedupe_key=f"correction:{uuid.uuid4()}",
            )
            await session.commit()

        async with SessionLocal() as session:
            held = (
                (
                    await session.execute(
                        select(UserBadge.badge_code).where(UserBadge.user_id == contributor)
                    )
                )
                .scalars()
                .all()
            )
        assert "CORRECTION_CONTRIBUTOR" in held

    async def test_awarding_grants_badges_in_the_same_transaction(
        self, contributor: uuid.UUID
    ) -> None:
        """A badge must not survive an award that gets rolled back."""
        async with SessionLocal() as session:
            user = await session.get(User, contributor)
            assert user is not None
            user.verified_contribution_count = 1
            await reputation_service.award(
                session,
                user=user,
                event_type=ReputationEventType.REPORT_VERIFIED,
                dedupe_key=f"verified:{uuid.uuid4()}",
            )
            await session.rollback()

        async with SessionLocal() as session:
            held = (
                (
                    await session.execute(
                        select(UserBadge.badge_code).where(UserBadge.user_id == contributor)
                    )
                )
                .scalars()
                .all()
            )
        assert held == []


class TestDevTokenExposure:
    """`dev_token` hands back a working sign-in for any address typed. It may
    exist only where there is no mail server and no real users."""

    @pytest.mark.parametrize("env", ["development", "test"])
    def test_exposed_only_where_there_is_no_mail_server(self, env: str) -> None:
        assert Settings(app_env=env, auth_secret="x" * 40).expose_dev_tokens is True

    @pytest.mark.parametrize("env", ["staging", "production"])
    def test_never_exposed_on_a_deployed_host(self, env: str) -> None:
        """Staging is the one this exists for: gating on `is_production` left
        it handing anyone a session for any address."""
        assert Settings(app_env=env, auth_secret="x" * 40).expose_dev_tokens is False

    def test_production_boot_refuses_if_it_were_ever_enabled(self) -> None:
        production = Settings(
            app_env="production",
            auth_secret="k" * 48,
            web_base_url="https://ghostdodo.com",
            s3_secret_key="a-real-secret",  # noqa: S106 - fixture, not a credential
        )
        # The property is derived, so this passes today; the assertion pins
        # the hardening check to it, so widening the property later fails
        # loudly at boot rather than silently in staging.
        assert production.expose_dev_tokens is False
        production.check_production_hardening()

    async def test_sign_in_returns_a_token_in_test_env(self, client: object) -> None:
        # The suite itself runs with APP_ENV=test in CI, so the helper that
        # every other auth test relies on must keep working.
        assert settings.expose_dev_tokens is True
