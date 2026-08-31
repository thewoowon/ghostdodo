"""Aggregation of qualified observations into publishable company metrics.

Suppression rule: below the publishable bar, rates are returned as `None`
rather than as small numbers. A 100% ghost rate from two reports is not a
fact about a company, and the API must not hand the UI a number it would be
tempted to render.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime

from app.core.methodology import Methodology
from app.modules.metrics.qualification import (
    Observation,
    QualificationResult,
    QualifiedObservation,
    qualify_all,
)
from app.shared.enums import HiringStage, MetricEligibility, MetricWindow

_PUBLISHABLE_STATES = frozenset({MetricEligibility.PUBLISHABLE, MetricEligibility.HIGH_CONFIDENCE})


@dataclass(frozen=True, slots=True)
class StageMetrics:
    stage: HiringStage
    qualified_n: int
    response_rate: float | None
    ghost_rate: float | None
    median_response_days: float | None


@dataclass(frozen=True, slots=True)
class CompanyMetrics:
    window: MetricWindow
    window_start: date | None
    window_end: date
    qualified_n: int
    verified_ratio: float
    eligibility: MetricEligibility

    response_rate: float | None
    ghost_rate: float | None
    broken_promise_rate: float | None
    median_response_days: float | None
    promised_timeline_n: int

    stage_breakdown: list[StageMetrics] = field(default_factory=list)
    methodology_version: str = ""

    @property
    def is_publishable(self) -> bool:
        return self.eligibility in _PUBLISHABLE_STATES


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _median_days(items: list[QualifiedObservation]) -> float | None:
    """Median, never mean: a single six-month outlier must not define a
    company's typical response time (docs/06 §6)."""
    values = [o.response_days for o in items if o.response_days is not None]
    if not values:
        return None
    return round(statistics.median(values), 2)


def _stage_metrics(
    stage: HiringStage, items: list[QualifiedObservation], *, publish: bool
) -> StageMetrics:
    n = len(items)
    if not publish or n == 0:
        return StageMetrics(
            stage=stage,
            qualified_n=n,
            response_rate=None,
            ghost_rate=None,
            median_response_days=None,
        )
    responded = sum(1 for o in items if o.responded)
    ghosted = sum(1 for o in items if o.ghosted)
    return StageMetrics(
        stage=stage,
        qualified_n=n,
        response_rate=_ratio(responded, n),
        ghost_rate=_ratio(ghosted, n),
        median_response_days=_median_days(items),
    )


def compute(
    observations: list[Observation],
    *,
    methodology: Methodology,
    window: MetricWindow,
    now: datetime,
) -> tuple[CompanyMetrics, QualificationResult]:
    """Compute one window's metrics. Returns the qualification result too, so
    moderation tooling can explain exactly which reports were excluded."""
    today = now.date()
    window_days = window.days
    window_start = today.fromordinal(today.toordinal() - window_days) if window_days else None

    result = qualify_all(observations, methodology=methodology, now=now, window_start=window_start)
    qualified = result.qualified
    n = len(qualified)

    verified_n = sum(1 for o in qualified if o.observation.is_verified)
    verified_ratio = round(verified_n / n, 4) if n else 0.0

    eligibility = methodology.eligibility_for(n, verified_ratio)
    publish = eligibility in _PUBLISHABLE_STATES

    responded = sum(1 for o in qualified if o.responded)
    ghosted = sum(1 for o in qualified if o.ghosted)
    promised = [o for o in qualified if o.had_promise]
    broken = sum(1 for o in promised if o.broke_promise)

    by_stage: dict[HiringStage, list[QualifiedObservation]] = {}
    for o in qualified:
        by_stage.setdefault(o.observation.stage, []).append(o)

    metrics = CompanyMetrics(
        window=window,
        window_start=window_start,
        window_end=today,
        qualified_n=n,
        verified_ratio=verified_ratio,
        eligibility=eligibility,
        # Below the publishable bar the API returns no rates at all — the UI
        # renders `표본 부족` instead of a misleading percentage.
        response_rate=_ratio(responded, n) if publish else None,
        ghost_rate=_ratio(ghosted, n) if publish else None,
        broken_promise_rate=_ratio(broken, len(promised)) if publish else None,
        median_response_days=_median_days(qualified) if publish else None,
        promised_timeline_n=len(promised),
        stage_breakdown=[
            _stage_metrics(stage, by_stage.get(stage, []), publish=publish)
            for stage in HiringStage.ordered()
            if stage in by_stage
        ],
        methodology_version=methodology.version,
    )
    return metrics, result
