"""Observation qualification — the heart of the product's defensibility.

A raw report is not a measurement. Before an observation can move a company's
public numbers it must answer three questions:

  1. Is it eligible at all? (verified, not withdrawn, not a duplicate)
  2. Has enough time passed to call silence *silence*? (methodology windows)
  3. What did the company actually do? (responded / silent / broke a promise)

Every threshold comes from `app.core.methodology`. There are no numeric
literals for windows or grace periods in this module, by design: the public
methodology page and these functions must never disagree.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from app.core.methodology import Methodology
from app.shared.enums import (
    PUBLIC_REPORT_STATUSES,
    HiringStage,
    Outcome,
    SilenceSeverity,
    VerificationStatus,
)


class Disqualified(StrEnum):
    """Why an observation was excluded. Surfaced in moderation tooling so
    exclusions are explainable rather than mysterious."""

    NOT_PUBLIC_STATUS = "NOT_PUBLIC_STATUS"
    APPLICANT_WITHDREW = "APPLICANT_WITHDREW"
    WINDOW_NOT_ELAPSED = "WINDOW_NOT_ELAPSED"
    INSUFFICIENT_TIMING = "INSUFFICIENT_TIMING"
    OUTSIDE_WINDOW = "OUTSIDE_WINDOW"


@dataclass(frozen=True, slots=True)
class Observation:
    """The subset of a report that measurement actually reads.

    Kept as a plain value object so the calculation is testable without a
    database and cannot accidentally depend on reporter identity.
    """

    report_id: str
    stage: HiringStage
    application_date: date
    last_company_interaction_at: datetime | None
    promised_result: bool
    promised_result_date: date | None
    promised_window_end_date: date | None
    result_received: bool
    result_received_at: datetime | None
    outcome: Outcome
    verification_status: VerificationStatus

    @property
    def is_verified(self) -> bool:
        return self.verification_status is VerificationStatus.VERIFIED


@dataclass(frozen=True, slots=True)
class QualifiedObservation:
    observation: Observation
    responded: bool
    """A disposition was explicitly communicated. A rejection counts as a
    response — that principle is central to the product (docs/06 §4)."""

    ghosted: bool
    broke_promise: bool
    """Company stated a date, the grace period elapsed, and nothing arrived."""

    had_promise: bool
    response_days: float | None
    severity: SilenceSeverity


@dataclass(frozen=True, slots=True)
class QualificationResult:
    qualified: list[QualifiedObservation]
    excluded: dict[str, Disqualified]

    @property
    def n(self) -> int:
        return len(self.qualified)


def _anchor_datetime(obs: Observation) -> datetime | None:
    """The clock for silence starts at the last company-side interaction; if
    the company never interacted, it starts at the application itself."""
    if obs.last_company_interaction_at is not None:
        return obs.last_company_interaction_at
    return datetime.combine(obs.application_date, datetime.min.time(), tzinfo=UTC)


def _promise_deadline(obs: Observation, methodology: Methodology) -> date | None:
    """End of the promise window plus the configured grace period."""
    stated = obs.promised_window_end_date or obs.promised_result_date
    if stated is None:
        return None
    return stated + timedelta(days=methodology.promise_grace_days)


def _severity_for(stage: HiringStage, broke_promise: bool) -> SilenceSeverity:
    if broke_promise:
        return SilenceSeverity.L4_BROKEN_PROMISE
    if stage.order >= HiringStage.INTERVIEW_1.order:
        return SilenceSeverity.L3_INTERVIEW_GHOSTING
    if stage in (HiringStage.TEST, HiringStage.ASSIGNMENT):
        return SilenceSeverity.L2_ASSESSMENT_SILENCE
    return SilenceSeverity.L1_APPLICATION_SILENCE


def qualify(
    obs: Observation,
    *,
    methodology: Methodology,
    now: datetime,
    window_start: date | None = None,
) -> QualifiedObservation | Disqualified:
    """Classify one observation, or explain why it does not count."""
    if obs.verification_status not in PUBLIC_REPORT_STATUSES:
        return Disqualified.NOT_PUBLIC_STATUS

    # The applicant walking away tells us nothing about company behaviour.
    if obs.outcome is Outcome.WITHDREW:
        return Disqualified.APPLICANT_WITHDREW

    if window_start is not None and obs.application_date < window_start:
        return Disqualified.OUTSIDE_WINDOW

    anchor = _anchor_datetime(obs)
    if anchor is None:
        return Disqualified.INSUFFICIENT_TIMING

    had_promise = obs.promised_result and (
        obs.promised_result_date is not None or obs.promised_window_end_date is not None
    )

    if obs.result_received:
        if obs.result_received_at is None:
            return Disqualified.INSUFFICIENT_TIMING
        response_days = (obs.result_received_at - anchor).total_seconds() / 86400
        if response_days < 0:
            # Impossible timeline; auto-checks should have caught this earlier.
            return Disqualified.INSUFFICIENT_TIMING
        broke_promise = False
        if had_promise:
            deadline = _promise_deadline(obs, methodology)
            broke_promise = deadline is not None and obs.result_received_at.date() > deadline
        return QualifiedObservation(
            observation=obs,
            responded=True,
            ghosted=False,
            # A late-but-delivered result is still a missed promise, and is
            # reported separately from ghosting rather than folded into it.
            broke_promise=broke_promise,
            had_promise=had_promise,
            response_days=response_days,
            severity=SilenceSeverity.L0_INSUFFICIENT,
        )

    # No result yet. Has the company had long enough?
    elapsed_days = (now - anchor).total_seconds() / 86400
    stage_window = methodology.stage_threshold(obs.stage).silence_days

    promise_deadline = _promise_deadline(obs, methodology) if had_promise else None
    promise_overdue = promise_deadline is not None and now.date() > promise_deadline

    # An explicit promise is a stronger, faster signal than the generic stage
    # window: the company set the date itself.
    if not promise_overdue and elapsed_days < stage_window:
        return Disqualified.WINDOW_NOT_ELAPSED

    broke_promise = bool(promise_overdue)
    return QualifiedObservation(
        observation=obs,
        responded=False,
        ghosted=True,
        broke_promise=broke_promise,
        had_promise=had_promise,
        response_days=None,
        severity=_severity_for(obs.stage, broke_promise),
    )


def qualify_all(
    observations: list[Observation],
    *,
    methodology: Methodology,
    now: datetime,
    window_start: date | None = None,
) -> QualificationResult:
    qualified: list[QualifiedObservation] = []
    excluded: dict[str, Disqualified] = {}
    for obs in observations:
        result = qualify(obs, methodology=methodology, now=now, window_start=window_start)
        if isinstance(result, QualifiedObservation):
            qualified.append(result)
        else:
            excluded[obs.report_id] = result
    return QualificationResult(qualified=qualified, excluded=excluded)
