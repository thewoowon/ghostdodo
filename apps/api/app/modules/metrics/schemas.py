from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, cast

from pydantic import BaseModel

from app.modules.metrics.models import CompanyMetricSnapshot
from app.shared.enums import MetricEligibility, MetricWindow


class StageMetricsOut(BaseModel):
    stage: str
    qualified_n: int
    response_rate: float | None = None
    ghost_rate: float | None = None
    median_response_days: float | None = None


class CompanyMetricsOut(BaseModel):
    """Public metric response.

    Rates are nullable on purpose. Below the publishable sample bar every
    rate is `null` while `qualified_n`, `window`, and `eligibility` are still
    present — the client shows `표본 부족` rather than inventing a percentage
    (docs/08 §8).
    """

    company_id: uuid.UUID
    window: MetricWindow
    window_start: date | None
    window_end: date | None
    eligibility: MetricEligibility
    qualified_n: int
    verified_ratio: float
    response_rate: float | None
    ghost_rate: float | None
    broken_promise_rate: float | None
    median_response_days: float | None
    promised_timeline_n: int
    stage_breakdown: list[StageMetricsOut]
    methodology_version: str
    computed_at: datetime | None = None

    @classmethod
    def from_snapshot(cls, snapshot: CompanyMetricSnapshot) -> CompanyMetricsOut:
        raw = cast("Mapping[str, Mapping[str, Any]]", snapshot.stage_breakdown or {})
        breakdown = [
            StageMetricsOut(
                stage=stage,
                qualified_n=int(data.get("qualified_n", 0)),
                response_rate=data.get("response_rate"),
                ghost_rate=data.get("ghost_rate"),
                median_response_days=data.get("median_response_days"),
            )
            for stage, data in raw.items()
        ]
        return cls(
            company_id=snapshot.company_id,
            window=snapshot.window,
            window_start=snapshot.window_start,
            window_end=snapshot.window_end,
            eligibility=snapshot.eligibility,
            qualified_n=snapshot.qualified_n,
            verified_ratio=snapshot.verified_ratio,
            response_rate=snapshot.response_rate,
            ghost_rate=snapshot.ghost_rate,
            broken_promise_rate=snapshot.broken_promise_rate,
            median_response_days=snapshot.median_response_days,
            promised_timeline_n=snapshot.promised_timeline_n,
            stage_breakdown=breakdown,
            methodology_version=snapshot.methodology_version,
            computed_at=snapshot.computed_at,
        )

    @classmethod
    def empty(
        cls, *, company_id: uuid.UUID, window: MetricWindow, methodology_version: str
    ) -> CompanyMetricsOut:
        return cls(
            company_id=company_id,
            window=window,
            window_start=None,
            window_end=None,
            eligibility=MetricEligibility.INSUFFICIENT_DATA,
            qualified_n=0,
            verified_ratio=0.0,
            response_rate=None,
            ghost_rate=None,
            broken_promise_rate=None,
            median_response_days=None,
            promised_timeline_n=0,
            stage_breakdown=[],
            methodology_version=methodology_version,
        )
