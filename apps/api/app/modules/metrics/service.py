"""Metric snapshot persistence and cache invalidation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.methodology import Methodology, get_methodology
from app.modules.metrics.calculator import CompanyMetrics, compute
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.metrics.qualification import Observation
from app.modules.reports.models import RecruitmentExperience
from app.shared.enums import PUBLIC_REPORT_STATUSES, MetricWindow

log = get_logger(__name__)


async def _load_observations(session: AsyncSession, company_id: uuid.UUID) -> list[Observation]:
    """Loads only the columns measurement needs. `user_id` is not among them,
    so the aggregation path cannot depend on reporter identity even by
    accident."""
    stmt = select(
        RecruitmentExperience.id,
        RecruitmentExperience.furthest_stage,
        RecruitmentExperience.application_date,
        RecruitmentExperience.last_company_interaction_at,
        RecruitmentExperience.promised_result,
        RecruitmentExperience.promised_result_date,
        RecruitmentExperience.promised_window_end_date,
        RecruitmentExperience.result_received,
        RecruitmentExperience.result_received_at,
        RecruitmentExperience.outcome,
        RecruitmentExperience.verification_status,
    ).where(
        RecruitmentExperience.company_id == company_id,
        RecruitmentExperience.verification_status.in_(PUBLIC_REPORT_STATUSES),
    )
    rows = (await session.execute(stmt)).all()
    return [
        Observation(
            report_id=str(r.id),
            stage=r.furthest_stage,
            application_date=r.application_date,
            last_company_interaction_at=r.last_company_interaction_at,
            promised_result=r.promised_result,
            promised_result_date=r.promised_result_date,
            promised_window_end_date=r.promised_window_end_date,
            result_received=r.result_received,
            result_received_at=r.result_received_at,
            outcome=r.outcome,
            verification_status=r.verification_status,
        )
        for r in rows
    ]


async def recompute_company(
    session: AsyncSession,
    company_id: uuid.UUID,
    *,
    methodology: Methodology | None = None,
    now: datetime | None = None,
) -> dict[MetricWindow, CompanyMetrics]:
    """Recompute and persist every window for one company.

    Called after any verification status change, so a company page never
    aggregates raw rows at request time (docs/05 §7).
    """
    methodology = methodology or get_methodology()
    now = now or datetime.now(UTC)
    observations = await _load_observations(session, company_id)

    computed: dict[MetricWindow, CompanyMetrics] = {}
    for window in MetricWindow:
        metrics, _ = compute(observations, methodology=methodology, window=window, now=now)
        computed[window] = metrics
        await _upsert_snapshot(session, company_id, metrics)

    await session.flush()
    log.info(
        "metrics.recomputed",
        company_id=str(company_id),
        observations=len(observations),
        methodology=methodology.version,
    )
    return computed


async def _upsert_snapshot(
    session: AsyncSession, company_id: uuid.UUID, metrics: CompanyMetrics
) -> None:
    stage_breakdown = {
        s.stage.value: {
            "qualified_n": s.qualified_n,
            "response_rate": s.response_rate,
            "ghost_rate": s.ghost_rate,
            "median_response_days": s.median_response_days,
        }
        for s in metrics.stage_breakdown
    }
    values = {
        "company_id": company_id,
        "window": metrics.window,
        "window_start": metrics.window_start,
        "window_end": metrics.window_end,
        "qualified_n": metrics.qualified_n,
        "verified_ratio": metrics.verified_ratio,
        "response_rate": metrics.response_rate,
        "ghost_rate": metrics.ghost_rate,
        "broken_promise_rate": metrics.broken_promise_rate,
        "median_response_days": metrics.median_response_days,
        "promised_timeline_n": metrics.promised_timeline_n,
        "eligibility": metrics.eligibility,
        "stage_breakdown": stage_breakdown,
        "methodology_version": metrics.methodology_version,
        "computed_at": datetime.now(UTC),
    }
    stmt = pg_insert(CompanyMetricSnapshot).values(**values)
    await session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_metric_snapshot_company_window",
            set_={k: v for k, v in values.items() if k not in ("company_id", "window")},
        )
    )


async def get_snapshot(
    session: AsyncSession, company_id: uuid.UUID, window: MetricWindow
) -> CompanyMetricSnapshot | None:
    return (
        await session.execute(
            select(CompanyMetricSnapshot).where(
                CompanyMetricSnapshot.company_id == company_id,
                CompanyMetricSnapshot.window == window,
            )
        )
    ).scalar_one_or_none()
