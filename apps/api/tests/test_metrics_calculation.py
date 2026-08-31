"""Tests for the qualification + aggregation rules.

These encode product promises, not just code behaviour:
  * a rejection email is a successful response
  * silence is not called silence before the window elapses
  * small samples publish no rates at all
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.core.methodology import get_methodology
from app.modules.metrics.calculator import compute
from app.modules.metrics.qualification import Disqualified, Observation, qualify
from app.shared.enums import (
    HiringStage,
    MetricEligibility,
    MetricWindow,
    Outcome,
    SilenceSeverity,
    VerificationStatus,
)

METHODOLOGY = get_methodology()
NOW = datetime(2026, 9, 1, tzinfo=UTC)


def make_obs(
    *,
    report_id: str = "r1",
    stage: HiringStage = HiringStage.INTERVIEW_1,
    days_since_interaction: int = 60,
    result_received: bool = False,
    response_days: int | None = None,
    outcome: Outcome = Outcome.UNKNOWN,
    promised_result: bool = False,
    promised_result_date: date | None = None,
    status: VerificationStatus = VerificationStatus.VERIFIED,
) -> Observation:
    last_interaction = NOW - timedelta(days=days_since_interaction)
    received_at = (
        last_interaction + timedelta(days=response_days)
        if result_received and response_days is not None
        else None
    )
    return Observation(
        report_id=report_id,
        stage=stage,
        application_date=(last_interaction - timedelta(days=14)).date(),
        last_company_interaction_at=last_interaction,
        promised_result=promised_result,
        promised_result_date=promised_result_date,
        promised_window_end_date=None,
        result_received=result_received,
        result_received_at=received_at,
        outcome=outcome,
        verification_status=status,
    )


class TestQualification:
    def test_rejection_counts_as_a_response(self) -> None:
        """The product's central principle: being told no is being answered."""
        result = qualify(
            make_obs(result_received=True, response_days=5, outcome=Outcome.REJECTED),
            methodology=METHODOLOGY,
            now=NOW,
        )
        assert not isinstance(result, Disqualified)
        assert result.responded is True
        assert result.ghosted is False
        assert result.response_days == pytest.approx(5.0)

    def test_silence_within_stage_window_does_not_qualify(self) -> None:
        """A merely slow company is not a silent one."""
        window = METHODOLOGY.stage_threshold(HiringStage.INTERVIEW_1).silence_days
        result = qualify(
            make_obs(days_since_interaction=window - 1),
            methodology=METHODOLOGY,
            now=NOW,
        )
        assert result is Disqualified.WINDOW_NOT_ELAPSED

    def test_silence_past_stage_window_qualifies_as_ghosted(self) -> None:
        window = METHODOLOGY.stage_threshold(HiringStage.INTERVIEW_1).silence_days
        result = qualify(
            make_obs(days_since_interaction=window + 1),
            methodology=METHODOLOGY,
            now=NOW,
        )
        assert not isinstance(result, Disqualified)
        assert result.ghosted is True
        assert result.severity is SilenceSeverity.L3_INTERVIEW_GHOSTING

    def test_applicant_withdrawal_is_excluded(self) -> None:
        """Says nothing about the company, so it must not move the numbers."""
        result = qualify(make_obs(outcome=Outcome.WITHDREW), methodology=METHODOLOGY, now=NOW)
        assert result is Disqualified.APPLICANT_WITHDREW

    def test_unverified_report_is_excluded(self) -> None:
        result = qualify(
            make_obs(status=VerificationStatus.SUBMITTED), methodology=METHODOLOGY, now=NOW
        )
        assert result is Disqualified.NOT_PUBLIC_STATUS

    def test_broken_promise_uses_grace_period(self) -> None:
        """A promise is a faster clock than the generic stage window, but the
        company still gets the configured grace period first."""
        promised = (NOW - timedelta(days=METHODOLOGY.promise_grace_days + 2)).date()
        obs = make_obs(
            stage=HiringStage.APPLICATION,  # long stage window, not yet elapsed
            days_since_interaction=10,
            promised_result=True,
            promised_result_date=promised,
        )
        result = qualify(obs, methodology=METHODOLOGY, now=NOW)
        assert not isinstance(result, Disqualified)
        assert result.broke_promise is True
        assert result.severity is SilenceSeverity.L4_BROKEN_PROMISE

    def test_promise_still_within_grace_does_not_qualify(self) -> None:
        promised = (NOW - timedelta(days=METHODOLOGY.promise_grace_days - 1)).date()
        obs = make_obs(
            stage=HiringStage.APPLICATION,
            days_since_interaction=10,
            promised_result=True,
            promised_result_date=promised,
        )
        assert qualify(obs, methodology=METHODOLOGY, now=NOW) is Disqualified.WINDOW_NOT_ELAPSED

    def test_late_but_delivered_result_is_response_and_broken_promise(self) -> None:
        """Both facts are true and are reported separately — a late answer is
        still an answer."""
        obs = make_obs(
            days_since_interaction=60,
            result_received=True,
            response_days=50,
            outcome=Outcome.REJECTED,
            promised_result=True,
            promised_result_date=(NOW - timedelta(days=55)).date(),
        )
        result = qualify(obs, methodology=METHODOLOGY, now=NOW)
        assert not isinstance(result, Disqualified)
        assert result.responded is True
        assert result.ghosted is False
        assert result.broke_promise is True

    def test_impossible_timeline_is_excluded(self) -> None:
        obs = make_obs(result_received=True, response_days=-5)
        assert qualify(obs, methodology=METHODOLOGY, now=NOW) is Disqualified.INSUFFICIENT_TIMING


class TestAggregation:
    def test_tiny_sample_publishes_no_rates(self) -> None:
        """The suppression guarantee: 2 reports must not yield a percentage."""
        observations = [make_obs(report_id=f"r{i}", days_since_interaction=60) for i in range(2)]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        assert metrics.eligibility is MetricEligibility.INSUFFICIENT_DATA
        assert metrics.ghost_rate is None
        assert metrics.response_rate is None
        # Sample size itself is always disclosed.
        assert metrics.qualified_n == 2

    def test_early_signal_still_suppresses_rates(self) -> None:
        observations = [make_obs(report_id=f"r{i}", days_since_interaction=60) for i in range(6)]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        assert metrics.eligibility is MetricEligibility.EARLY_SIGNAL
        assert metrics.ghost_rate is None

    def test_publishable_sample_reports_rates(self) -> None:
        # 20 observations, 5 ghosted -> 25% ghost rate, all verified.
        observations = [
            make_obs(report_id=f"g{i}", days_since_interaction=60) for i in range(5)
        ] + [
            make_obs(
                report_id=f"ok{i}",
                days_since_interaction=60,
                result_received=True,
                response_days=7,
                outcome=Outcome.REJECTED,
            )
            for i in range(15)
        ]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        assert metrics.eligibility is MetricEligibility.PUBLISHABLE
        assert metrics.qualified_n == 20
        assert metrics.ghost_rate == pytest.approx(0.25)
        assert metrics.response_rate == pytest.approx(0.75)
        assert metrics.median_response_days == pytest.approx(7.0)

    def test_rates_are_complementary(self) -> None:
        observations = [
            make_obs(report_id=f"g{i}", days_since_interaction=60) for i in range(8)
        ] + [
            make_obs(
                report_id=f"ok{i}",
                days_since_interaction=60,
                result_received=True,
                response_days=3,
                outcome=Outcome.PASSED,
            )
            for i in range(12)
        ]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        assert metrics.response_rate is not None and metrics.ghost_rate is not None
        assert metrics.response_rate + metrics.ghost_rate == pytest.approx(1.0)

    def test_median_ignores_a_single_outlier(self) -> None:
        observations = [
            make_obs(
                report_id=f"r{i}",
                days_since_interaction=200,
                result_received=True,
                response_days=5,
                outcome=Outcome.REJECTED,
            )
            for i in range(19)
        ] + [
            make_obs(
                report_id="outlier",
                days_since_interaction=400,
                result_received=True,
                response_days=300,
                outcome=Outcome.REJECTED,
            )
        ]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.ALL, now=NOW
        )
        assert metrics.median_response_days == pytest.approx(5.0)

    def test_window_excludes_older_applications(self) -> None:
        recent = [make_obs(report_id=f"new{i}", days_since_interaction=30) for i in range(16)]
        old = [make_obs(report_id=f"old{i}", days_since_interaction=800) for i in range(10)]
        metrics, result = compute(
            recent + old, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        assert metrics.qualified_n == 16
        assert all(result.excluded[f"old{i}"] is Disqualified.OUTSIDE_WINDOW for i in range(10))

    def test_broken_promise_rate_denominator_is_promises_only(self) -> None:
        """Companies that never promise a date are not penalised in this rate."""
        promised_broken = [
            make_obs(
                report_id=f"p{i}",
                days_since_interaction=60,
                promised_result=True,
                promised_result_date=(NOW - timedelta(days=40)).date(),
            )
            for i in range(4)
        ]
        no_promise = [make_obs(report_id=f"n{i}", days_since_interaction=60) for i in range(16)]
        metrics, _ = compute(
            promised_broken + no_promise,
            methodology=METHODOLOGY,
            window=MetricWindow.W12M,
            now=NOW,
        )
        assert metrics.promised_timeline_n == 4
        assert metrics.broken_promise_rate == pytest.approx(1.0)

    def test_stage_breakdown_covers_present_stages_only(self) -> None:
        observations = [
            make_obs(report_id=f"a{i}", stage=HiringStage.APPLICATION, days_since_interaction=60)
            for i in range(10)
        ] + [
            make_obs(
                report_id=f"i{i}",
                stage=HiringStage.FINAL_INTERVIEW,
                days_since_interaction=60,
            )
            for i in range(10)
        ]
        metrics, _ = compute(
            observations, methodology=METHODOLOGY, window=MetricWindow.W12M, now=NOW
        )
        stages = [s.stage for s in metrics.stage_breakdown]
        assert stages == [HiringStage.APPLICATION, HiringStage.FINAL_INTERVIEW]
        assert sum(s.qualified_n for s in metrics.stage_breakdown) == metrics.qualified_n


class TestMethodologyConfiguration:
    def test_thresholds_come_from_methodology_not_literals(self) -> None:
        """Guards the docs/06 rule that thresholds stay configurable: later
        stages must never wait longer than earlier ones."""
        ordered = HiringStage.ordered()
        windows = [METHODOLOGY.stage_threshold(s).silence_days for s in ordered]
        assert windows == sorted(windows, reverse=True)

    def test_eligibility_ladder_is_monotonic(self) -> None:
        assert (
            METHODOLOGY.eligibility[MetricEligibility.EARLY_SIGNAL].min_qualified_n
            < METHODOLOGY.eligibility[MetricEligibility.PUBLISHABLE].min_qualified_n
            < METHODOLOGY.eligibility[MetricEligibility.HIGH_CONFIDENCE].min_qualified_n
        )
