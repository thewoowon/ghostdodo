"""bootstrap: extensions and domain enum types

Enum values mirror `app.shared.enums`. Adding a value later requires an
`ALTER TYPE ... ADD VALUE` migration — the Python enum alone is not enough.

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Typo-tolerant Korean company search (trigram similarity on names/aliases).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    op.execute(
        "CREATE TYPE application_source AS ENUM ('COMPANY_SITE', 'SARAMIN', 'JOBKOREA', 'WANTED', 'JUMPIT', 'PROGRAMMERS', 'ROCKETPUNCH', 'REMEMBER', 'LINKEDIN', 'REFERRAL', 'RECRUITER_OUTREACH', 'OTHER')"
    )
    op.execute(
        "CREATE TYPE audit_action AS ENUM ('MODERATION_DECISION', 'VERIFICATION_STATUS_CHANGED', 'EVIDENCE_ACCESSED', 'EVIDENCE_DELETED', 'COMPANY_CORRECTION', 'COMPANY_CLAIM_DECISION', 'USER_SANCTION', 'METRIC_RECOMPUTED')"
    )
    op.execute(
        "CREATE TYPE communication_channel AS ENUM ('EMAIL', 'SMS', 'PHONE', 'JOB_BOARD', 'MESSENGER', 'IN_PERSON', 'OTHER')"
    )
    op.execute(
        "CREATE TYPE company_claim_state AS ENUM ('UNCLAIMED', 'CLAIM_PENDING', 'CLAIMED', 'CLAIM_REVOKED')"
    )
    op.execute(
        "CREATE TYPE company_size_band AS ENUM ('UNKNOWN', 'B1_9', 'B10_49', 'B50_199', 'B200_999', 'B1000_PLUS')"
    )
    op.execute(
        "CREATE TYPE credit_event_type AS ENUM ('CONTRIBUTION_REWARD', 'VERIFICATION_BONUS', 'FIRST_OBSERVATION_BONUS', 'COSMETIC_PURCHASE', 'ADJUSTMENT', 'REVERSAL')"
    )
    op.execute(
        "CREATE TYPE employment_type AS ENUM ('FULL_TIME', 'CONTRACT', 'INTERN', 'PART_TIME', 'FREELANCE', 'DISPATCH')"
    )
    op.execute(
        "CREATE TYPE evidence_access_state AS ENUM ('UPLOAD_PENDING', 'AVAILABLE', 'QUARANTINED', 'DELETED')"
    )
    op.execute(
        "CREATE TYPE evidence_review_state AS ENUM ('PENDING', 'CLEAN', 'PII_SUSPECTED', 'REDACTED', 'REJECTED')"
    )
    op.execute(
        "CREATE TYPE hiring_stage AS ENUM ('APPLICATION', 'DOCUMENT_SCREENING', 'TEST', 'ASSIGNMENT', 'INTERVIEW_1', 'INTERVIEW_2_PLUS', 'FINAL_INTERVIEW', 'OFFER_COMPENSATION')"
    )
    op.execute(
        "CREATE TYPE metric_eligibility AS ENUM ('INSUFFICIENT_DATA', 'EARLY_SIGNAL', 'PUBLISHABLE', 'HIGH_CONFIDENCE')"
    )
    op.execute("CREATE TYPE metric_window AS ENUM ('6m', '12m', 'all')")
    op.execute("CREATE TYPE outcome AS ENUM ('PASSED', 'REJECTED', 'WITHDREW', 'UNKNOWN')")
    op.execute(
        "CREATE TYPE reputation_event_type AS ENUM ('REPORT_SUBMITTED_COMPLETE', 'REPORT_VERIFIED', 'EVIDENCE_VERIFIED', 'REPORT_CORROBORATED', 'FACTUAL_CORRECTION_ACCEPTED', 'COMPANY_METADATA_ACCEPTED', 'PII_FLAG_ACCEPTED', 'HELPFUL_COMMUNITY_ANSWER', 'REPORT_REVERSED', 'MODERATION_SANCTION')"
    )
    op.execute(
        "CREATE TYPE reputation_rank AS ENUM ('OBSERVER', 'EXPLORER', 'RECORDER', 'VERIFIER', 'ARCHIVIST', 'DODO_RANGER')"
    )
    op.execute(
        "CREATE TYPE review_decision AS ENUM ('VERIFY', 'PARTIALLY_VERIFY', 'REJECT', 'REQUEST_REDACTION', 'MARK_DISPUTED', 'REMOVE')"
    )
    op.execute(
        "CREATE TYPE role_category AS ENUM ('SOFTWARE_ENGINEERING', 'DATA', 'DESIGN', 'PRODUCT', 'MARKETING', 'SALES', 'OPERATIONS', 'HR', 'FINANCE', 'CUSTOMER_SUPPORT', 'RESEARCH', 'MANUFACTURING', 'OTHER')"
    )
    op.execute(
        "CREATE TYPE silence_severity AS ENUM ('L0_INSUFFICIENT', 'L1_APPLICATION_SILENCE', 'L2_ASSESSMENT_SILENCE', 'L3_INTERVIEW_GHOSTING', 'L4_BROKEN_PROMISE')"
    )
    op.execute(
        "CREATE TYPE stage_event_type AS ENUM ('APPLIED', 'COMPANY_ACKNOWLEDGED', 'STAGE_INVITED', 'STAGE_COMPLETED', 'RESULT_PROMISED', 'RESULT_RECEIVED', 'APPLICANT_FOLLOWED_UP', 'APPLICANT_WITHDREW')"
    )
    op.execute("CREATE TYPE trust_state AS ENUM ('NEW', 'ACTIVE', 'RESTRICTED', 'SUSPENDED')")
    op.execute("CREATE TYPE user_role AS ENUM ('USER', 'MODERATOR', 'ADMIN', 'COMPANY_REP')")
    op.execute(
        "CREATE TYPE verification_status AS ENUM ('DRAFT', 'SUBMITTED', 'AUTO_CHECKED', 'NEEDS_REVIEW', 'VERIFIED', 'PARTIALLY_VERIFIED', 'REJECTED', 'DISPUTED', 'REDACTED', 'REMOVED')"
    )


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS verification_status")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS trust_state")
    op.execute("DROP TYPE IF EXISTS stage_event_type")
    op.execute("DROP TYPE IF EXISTS silence_severity")
    op.execute("DROP TYPE IF EXISTS role_category")
    op.execute("DROP TYPE IF EXISTS review_decision")
    op.execute("DROP TYPE IF EXISTS reputation_rank")
    op.execute("DROP TYPE IF EXISTS reputation_event_type")
    op.execute("DROP TYPE IF EXISTS outcome")
    op.execute("DROP TYPE IF EXISTS metric_window")
    op.execute("DROP TYPE IF EXISTS metric_eligibility")
    op.execute("DROP TYPE IF EXISTS hiring_stage")
    op.execute("DROP TYPE IF EXISTS evidence_review_state")
    op.execute("DROP TYPE IF EXISTS evidence_access_state")
    op.execute("DROP TYPE IF EXISTS employment_type")
    op.execute("DROP TYPE IF EXISTS credit_event_type")
    op.execute("DROP TYPE IF EXISTS company_size_band")
    op.execute("DROP TYPE IF EXISTS company_claim_state")
    op.execute("DROP TYPE IF EXISTS communication_channel")
    op.execute("DROP TYPE IF EXISTS audit_action")
    op.execute("DROP TYPE IF EXISTS application_source")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
