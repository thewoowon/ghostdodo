"""Report drafting, submission, and automated pre-checks."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.methodology import CURRENT_METHODOLOGY_VERSION, Methodology
from app.modules.metrics.qualification import Observation, QualifiedObservation, qualify
from app.modules.reports.models import RecruitmentExperience, RecruitmentStageEvent
from app.modules.reports.schemas import ReportInput, ReportUpdate
from app.shared.enums import (
    USER_EDITABLE_REPORT_STATUSES,
    CommunicationChannel,
    HiringStage,
    SilenceSeverity,
    StageEventType,
    VerificationStatus,
)
from app.shared.errors import (
    DuplicateReportError,
    ReportLimitError,
    ReportNotEditableError,
    ReportNotFoundError,
)


def compute_dedupe_hash(
    user_id: uuid.UUID, company_id: uuid.UUID, stage: HiringStage, application_date: date
) -> str:
    """Same person, same company, same stage, same month is almost always one
    process reported twice — not two observations."""
    raw = f"{user_id}:{company_id}:{stage.value}:{application_date:%Y-%m}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_draft(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: ReportInput,
    idempotency_key: str | None = None,
) -> RecruitmentExperience:
    if idempotency_key:
        existing = (
            await session.execute(
                select(RecruitmentExperience).where(
                    RecruitmentExperience.user_id == user_id,
                    RecruitmentExperience.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            # Replaying the same request returns the same report rather than
            # creating a second one.
            return existing

    report = RecruitmentExperience(
        user_id=user_id,
        idempotency_key=idempotency_key,
        verification_status=VerificationStatus.DRAFT,
        **payload.model_dump(),
    )
    session.add(report)
    await session.flush()
    return report


async def get_own_report(
    session: AsyncSession, *, report_id: uuid.UUID, user_id: uuid.UUID
) -> RecruitmentExperience:
    report = await session.get(RecruitmentExperience, report_id)
    if report is None or report.user_id != user_id:
        # Same error for "missing" and "someone else's": a 403 would confirm
        # the report exists.
        raise ReportNotFoundError()
    return report


async def update_draft(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ReportUpdate,
) -> RecruitmentExperience:
    report = await get_own_report(session, report_id=report_id, user_id=user_id)
    if report.verification_status not in USER_EDITABLE_REPORT_STATUSES:
        raise ReportNotEditableError()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    await session.flush()
    return report


def run_auto_checks(report: RecruitmentExperience, *, now: datetime) -> dict[str, object]:
    """Cheap structural checks run at submission (docs/05 §6). These route a
    report to review; they never auto-reject, because a false positive would
    silently discard a real observation."""
    flags: dict[str, object] = {}

    if report.application_date > now.date():
        flags["impossible_application_date"] = True
    if report.result_received_at and report.result_received_at > now:
        flags["future_result_date"] = True
    if (
        report.last_company_interaction_at
        and report.last_company_interaction_at.date() < report.application_date
    ):
        flags["interaction_before_application"] = True
    if report.promised_result_date and report.promised_result_date < report.application_date:
        flags["promise_before_application"] = True

    if report.free_context:
        text = report.free_context
        # PII heuristics: Korean mobile numbers, emails, and long digit runs.
        if "@" in text or _looks_like_phone(text):
            flags["possible_pii"] = True

    age_days = (now.date() - report.application_date).days
    if age_days > 365 * 3:
        flags["very_old_application"] = True

    return flags


def _looks_like_phone(text: str) -> bool:
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) >= 9


async def submit_report(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    methodology: Methodology,
    now: datetime | None = None,
) -> RecruitmentExperience:
    """Move a draft into the verification pipeline.

    Runs duplicate and volume protection, records the severity under the
    current methodology, and generates the stage timeline that becomes the
    public Ghostory.
    """
    now = now or datetime.now(UTC)
    report = await get_own_report(session, report_id=report_id, user_id=user_id)

    if report.verification_status is not VerificationStatus.DRAFT:
        raise ReportNotEditableError("이미 제출된 기록입니다.")

    dedupe_hash = compute_dedupe_hash(
        user_id, report.company_id, report.furthest_stage, report.application_date
    )
    duplicate = (
        await session.execute(
            select(RecruitmentExperience.id).where(
                RecruitmentExperience.dedupe_hash == dedupe_hash,
                RecruitmentExperience.id != report.id,
                RecruitmentExperience.verification_status != VerificationStatus.REJECTED,
            )
        )
    ).first()
    if duplicate is not None:
        raise DuplicateReportError()

    submitted_count = (
        await session.execute(
            select(func.count(RecruitmentExperience.id)).where(
                RecruitmentExperience.user_id == user_id,
                RecruitmentExperience.company_id == report.company_id,
                RecruitmentExperience.verification_status.notin_(
                    [VerificationStatus.DRAFT, VerificationStatus.REJECTED]
                ),
            )
        )
    ).scalar_one()
    if submitted_count >= methodology.max_reports_per_user_per_company:
        raise ReportLimitError()

    report.dedupe_hash = dedupe_hash
    report.submitted_at = now
    report.methodology_version = CURRENT_METHODOLOGY_VERSION
    report.severity = _severity_at_submission(report, methodology=methodology, now=now)

    flags = run_auto_checks(report, now=now)
    report.auto_check_flags = flags
    # Anything the checks flagged goes to a human; the rest still gets
    # reviewed, just in the ordinary queue.
    report.verification_status = (
        VerificationStatus.NEEDS_REVIEW if flags else VerificationStatus.AUTO_CHECKED
    )

    _rebuild_stage_events(report)
    await session.flush()
    return report


def _severity_at_submission(
    report: RecruitmentExperience, *, methodology: Methodology, now: datetime
) -> SilenceSeverity:
    outcome = qualify(
        Observation(
            report_id=str(report.id),
            stage=report.furthest_stage,
            application_date=report.application_date,
            last_company_interaction_at=report.last_company_interaction_at,
            promised_result=report.promised_result,
            promised_result_date=report.promised_result_date,
            promised_window_end_date=report.promised_window_end_date,
            result_received=report.result_received,
            result_received_at=report.result_received_at,
            outcome=report.outcome,
            # Severity describes the observation, not its review state, so
            # qualify against the status it will hold once verified.
            verification_status=VerificationStatus.VERIFIED,
        ),
        methodology=methodology,
        now=now,
    )
    if isinstance(outcome, QualifiedObservation):
        return outcome.severity
    return SilenceSeverity.L0_INSUFFICIENT


def _rebuild_stage_events(report: RecruitmentExperience) -> None:
    """Derive the timeline from the structured fields, so the public Ghostory
    always matches the record it came from."""
    report.stage_events.clear()

    events: list[RecruitmentStageEvent] = [
        RecruitmentStageEvent(
            event_type=StageEventType.APPLIED,
            stage=HiringStage.APPLICATION,
            occurred_at=datetime.combine(report.application_date, datetime.min.time(), tzinfo=UTC),
        )
    ]

    if report.furthest_stage is not HiringStage.APPLICATION and report.last_company_interaction_at:
        events.append(
            RecruitmentStageEvent(
                event_type=StageEventType.STAGE_COMPLETED,
                stage=report.furthest_stage,
                occurred_at=report.last_company_interaction_at,
            )
        )

    if report.promised_result:
        promised = report.promised_result_date or report.promised_window_end_date
        if promised:
            events.append(
                RecruitmentStageEvent(
                    event_type=StageEventType.RESULT_PROMISED,
                    stage=report.furthest_stage,
                    occurred_at=datetime.combine(promised, datetime.min.time(), tzinfo=UTC),
                )
            )

    if report.result_received and report.result_received_at:
        events.append(
            RecruitmentStageEvent(
                event_type=StageEventType.RESULT_RECEIVED,
                stage=report.furthest_stage,
                occurred_at=report.result_received_at,
                channel=report.result_channel or CommunicationChannel.OTHER,
            )
        )

    events.sort(key=lambda e: e.occurred_at)
    report.stage_events.extend(events)
