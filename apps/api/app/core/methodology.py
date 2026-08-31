"""Versioned measurement methodology.

Every threshold that decides whether an observation counts as ghosted,
whether a company's numbers may be published, or how long a company gets
before silence is called silence, lives HERE — never inline in service code.

Rules:
  * Business logic reads thresholds through `get_methodology()`. It must not
    contain numeric literals for windows, grace periods, or sample sizes.
  * Changing any number requires a NEW version id. Snapshots record the
    version they were computed under, so historical numbers stay explainable
    and the public methodology page can describe exactly one ruleset.
  * Sponsorship, claim status, or ad spend must never appear here. Metrics
    are not purchasable (docs/06 §9).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.shared.enums import HiringStage, MetricEligibility

CURRENT_METHODOLOGY_VERSION = "2026-09-v1"


@dataclass(frozen=True, slots=True)
class StageThreshold:
    """How long silence must last, per stage, before it is *observable*.

    `silence_days` is measured from the last company-side interaction. The
    values are deliberately conservative: a company that is merely slow must
    not be recorded as having gone silent.
    """

    silence_days: int
    analytic_weight: float
    """Relative weight in severity-aware aggregates. Later-stage silence is
    more informative, but public copy stays factual either way (docs/01 §6)."""


@dataclass(frozen=True, slots=True)
class EligibilityThreshold:
    min_qualified_n: int
    min_verified_ratio: float


@dataclass(frozen=True, slots=True)
class Methodology:
    version: str

    stage_thresholds: Mapping[HiringStage, StageThreshold]
    """Per-stage observation windows."""

    promise_grace_days: int
    """Extra days granted after a company's own stated result date before a
    promise is treated as missed. Distinct from stage silence windows: an
    explicit promise is a stronger signal, so the grace period is short."""

    eligibility: Mapping[MetricEligibility, EligibilityThreshold]
    """Sample-size protection ladder. Read in descending strictness."""

    recency_windows: tuple[str, ...]
    default_public_window: str

    max_reports_per_user_per_company: int
    """Duplicate suppression: the same person reporting the same company many
    times must not move an aggregate."""

    corroboration_min_independent_users: int
    """Independent reporters needed before an observation counts as
    corroborated for reputation purposes."""

    def stage_threshold(self, stage: HiringStage) -> StageThreshold:
        return self.stage_thresholds[stage]

    def eligibility_for(self, qualified_n: int, verified_ratio: float) -> MetricEligibility:
        """Classify a sample. Returns the strongest state whose bar is met."""
        for state in (
            MetricEligibility.HIGH_CONFIDENCE,
            MetricEligibility.PUBLISHABLE,
            MetricEligibility.EARLY_SIGNAL,
        ):
            bar = self.eligibility[state]
            if qualified_n >= bar.min_qualified_n and verified_ratio >= bar.min_verified_ratio:
                return state
        return MetricEligibility.INSUFFICIENT_DATA


_V1 = Methodology(
    version="2026-09-v1",
    stage_thresholds=MappingProxyType(
        {
            # Early stages: many companies genuinely batch-process for weeks.
            HiringStage.APPLICATION: StageThreshold(silence_days=45, analytic_weight=1.0),
            HiringStage.DOCUMENT_SCREENING: StageThreshold(silence_days=35, analytic_weight=1.0),
            # The applicant has now spent real hours.
            HiringStage.TEST: StageThreshold(silence_days=28, analytic_weight=1.5),
            HiringStage.ASSIGNMENT: StageThreshold(silence_days=28, analytic_weight=1.5),
            # Someone on the company side met them. Silence here is a choice.
            HiringStage.INTERVIEW_1: StageThreshold(silence_days=21, analytic_weight=2.0),
            HiringStage.INTERVIEW_2_PLUS: StageThreshold(silence_days=21, analytic_weight=2.0),
            HiringStage.FINAL_INTERVIEW: StageThreshold(silence_days=21, analytic_weight=2.5),
            HiringStage.OFFER_COMPENSATION: StageThreshold(silence_days=14, analytic_weight=2.5),
        }
    ),
    promise_grace_days=7,
    eligibility=MappingProxyType(
        {
            MetricEligibility.EARLY_SIGNAL: EligibilityThreshold(
                min_qualified_n=5, min_verified_ratio=0.0
            ),
            MetricEligibility.PUBLISHABLE: EligibilityThreshold(
                min_qualified_n=15, min_verified_ratio=0.30
            ),
            MetricEligibility.HIGH_CONFIDENCE: EligibilityThreshold(
                min_qualified_n=40, min_verified_ratio=0.50
            ),
        }
    ),
    recency_windows=("6m", "12m", "all"),
    default_public_window="12m",
    max_reports_per_user_per_company=3,
    corroboration_min_independent_users=2,
)

_REGISTRY: Mapping[str, Methodology] = MappingProxyType({_V1.version: _V1})


def get_methodology(version: str | None = None) -> Methodology:
    """Resolve a methodology version. `None` means the current one.

    Raises KeyError for unknown versions — an old snapshot referencing a
    deleted ruleset is a bug we want loud, not silently recomputed under
    today's rules.
    """
    return _REGISTRY[version or CURRENT_METHODOLOGY_VERSION]


def all_versions() -> tuple[str, ...]:
    return tuple(_REGISTRY)
