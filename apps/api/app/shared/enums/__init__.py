"""Centralized domain enums.

Every enum that crosses a module or API boundary lives here. Values are the
wire format: stable SCREAMING_SNAKE strings that appear in the API contract,
the database, and `packages/shared-types`. Never renumber or rename a value
without a migration and a shared-types regeneration.
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    COMPANY_REP = "COMPANY_REP"


class TrustState(StrEnum):
    """Contributor standing. Gates aggregate inclusion, not site access."""

    NEW = "NEW"
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    SUSPENDED = "SUSPENDED"


class CompanyClaimState(StrEnum):
    UNCLAIMED = "UNCLAIMED"
    CLAIM_PENDING = "CLAIM_PENDING"
    CLAIMED = "CLAIMED"
    CLAIM_REVOKED = "CLAIM_REVOKED"


class CompanySizeBand(StrEnum):
    UNKNOWN = "UNKNOWN"
    B1_9 = "B1_9"
    B10_49 = "B10_49"
    B50_199 = "B50_199"
    B200_999 = "B200_999"
    B1000_PLUS = "B1000_PLUS"


class RoleCategory(StrEnum):
    SOFTWARE_ENGINEERING = "SOFTWARE_ENGINEERING"
    DATA = "DATA"
    DESIGN = "DESIGN"
    PRODUCT = "PRODUCT"
    MARKETING = "MARKETING"
    SALES = "SALES"
    OPERATIONS = "OPERATIONS"
    HR = "HR"
    FINANCE = "FINANCE"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    RESEARCH = "RESEARCH"
    MANUFACTURING = "MANUFACTURING"
    OTHER = "OTHER"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"
    PART_TIME = "PART_TIME"
    FREELANCE = "FREELANCE"
    DISPATCH = "DISPATCH"


class ApplicationSource(StrEnum):
    """Where the application was submitted. Korean job boards are first-class."""

    COMPANY_SITE = "COMPANY_SITE"
    SARAMIN = "SARAMIN"
    JOBKOREA = "JOBKOREA"
    WANTED = "WANTED"
    JUMPIT = "JUMPIT"
    PROGRAMMERS = "PROGRAMMERS"
    ROCKETPUNCH = "ROCKETPUNCH"
    REMEMBER = "REMEMBER"
    LINKEDIN = "LINKEDIN"
    REFERRAL = "REFERRAL"
    RECRUITER_OUTREACH = "RECRUITER_OUTREACH"
    OTHER = "OTHER"


class HiringStage(StrEnum):
    """Ordered hiring funnel. `order()` is the analytic ordering — use it
    instead of comparing enum members, which compare as plain strings."""

    APPLICATION = "APPLICATION"
    DOCUMENT_SCREENING = "DOCUMENT_SCREENING"
    TEST = "TEST"
    ASSIGNMENT = "ASSIGNMENT"
    INTERVIEW_1 = "INTERVIEW_1"
    INTERVIEW_2_PLUS = "INTERVIEW_2_PLUS"
    FINAL_INTERVIEW = "FINAL_INTERVIEW"
    OFFER_COMPENSATION = "OFFER_COMPENSATION"

    @property
    def order(self) -> int:
        return _STAGE_ORDER[self]

    @classmethod
    def ordered(cls) -> list[HiringStage]:
        return sorted(cls, key=lambda s: s.order)


_STAGE_ORDER: dict[HiringStage, int] = {
    HiringStage.APPLICATION: 0,
    HiringStage.DOCUMENT_SCREENING: 1,
    HiringStage.TEST: 2,
    HiringStage.ASSIGNMENT: 3,
    HiringStage.INTERVIEW_1: 4,
    HiringStage.INTERVIEW_2_PLUS: 5,
    HiringStage.FINAL_INTERVIEW: 6,
    HiringStage.OFFER_COMPENSATION: 7,
}


class StageEventType(StrEnum):
    APPLIED = "APPLIED"
    COMPANY_ACKNOWLEDGED = "COMPANY_ACKNOWLEDGED"
    STAGE_INVITED = "STAGE_INVITED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    RESULT_PROMISED = "RESULT_PROMISED"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    APPLICANT_FOLLOWED_UP = "APPLICANT_FOLLOWED_UP"
    APPLICANT_WITHDREW = "APPLICANT_WITHDREW"


class CommunicationChannel(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PHONE = "PHONE"
    JOB_BOARD = "JOB_BOARD"
    MESSENGER = "MESSENGER"
    IN_PERSON = "IN_PERSON"
    OTHER = "OTHER"


class Outcome(StrEnum):
    PASSED = "PASSED"
    REJECTED = "REJECTED"
    WITHDREW = "WITHDREW"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(StrEnum):
    """Report lifecycle. Only VERIFIED / PARTIALLY_VERIFIED reports can enter
    public aggregates (see modules.metrics)."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AUTO_CHECKED = "AUTO_CHECKED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"
    REDACTED = "REDACTED"
    REMOVED = "REMOVED"


PUBLIC_REPORT_STATUSES: frozenset[VerificationStatus] = frozenset(
    {VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED}
)
"""Statuses whose reports may appear in public listings and aggregates."""

USER_EDITABLE_REPORT_STATUSES: frozenset[VerificationStatus] = frozenset({VerificationStatus.DRAFT})
"""Once review starts, corrections go through the dispute flow, not PATCH."""


class SilenceSeverity(StrEnum):
    """Severity taxonomy from docs/01. Not collapsed into one 'ghosted' bucket."""

    L0_INSUFFICIENT = "L0_INSUFFICIENT"
    L1_APPLICATION_SILENCE = "L1_APPLICATION_SILENCE"
    L2_ASSESSMENT_SILENCE = "L2_ASSESSMENT_SILENCE"
    L3_INTERVIEW_GHOSTING = "L3_INTERVIEW_GHOSTING"
    L4_BROKEN_PROMISE = "L4_BROKEN_PROMISE"


class MetricEligibility(StrEnum):
    """Sample-size protection state. Drives `표본 부족` suppression in the UI."""

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EARLY_SIGNAL = "EARLY_SIGNAL"
    PUBLISHABLE = "PUBLISHABLE"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"


class MetricWindow(StrEnum):
    W6M = "6m"
    W12M = "12m"
    ALL = "all"

    @property
    def days(self) -> int | None:
        return {MetricWindow.W6M: 183, MetricWindow.W12M: 365, MetricWindow.ALL: None}[self]


class EvidenceReviewState(StrEnum):
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    PII_SUSPECTED = "PII_SUSPECTED"
    REDACTED = "REDACTED"
    REJECTED = "REJECTED"


class EvidenceAccessState(StrEnum):
    """Evidence is never public. This tracks internal availability only."""

    UPLOAD_PENDING = "UPLOAD_PENDING"
    AVAILABLE = "AVAILABLE"
    QUARANTINED = "QUARANTINED"
    DELETED = "DELETED"


class ReviewDecision(StrEnum):
    VERIFY = "VERIFY"
    PARTIALLY_VERIFY = "PARTIALLY_VERIFY"
    REJECT = "REJECT"
    REQUEST_REDACTION = "REQUEST_REDACTION"
    MARK_DISPUTED = "MARK_DISPUTED"
    REMOVE = "REMOVE"


class ReputationEventType(StrEnum):
    """Reward completeness and verification — never negativity. See docs/07."""

    REPORT_SUBMITTED_COMPLETE = "REPORT_SUBMITTED_COMPLETE"
    REPORT_VERIFIED = "REPORT_VERIFIED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    REPORT_CORROBORATED = "REPORT_CORROBORATED"
    FACTUAL_CORRECTION_ACCEPTED = "FACTUAL_CORRECTION_ACCEPTED"
    COMPANY_METADATA_ACCEPTED = "COMPANY_METADATA_ACCEPTED"
    PII_FLAG_ACCEPTED = "PII_FLAG_ACCEPTED"
    HELPFUL_COMMUNITY_ANSWER = "HELPFUL_COMMUNITY_ANSWER"
    REPORT_REVERSED = "REPORT_REVERSED"
    MODERATION_SANCTION = "MODERATION_SANCTION"


class CreditEventType(StrEnum):
    """Dodo Credit is product utility, not currency. No cash-out, ever."""

    CONTRIBUTION_REWARD = "CONTRIBUTION_REWARD"
    VERIFICATION_BONUS = "VERIFICATION_BONUS"
    FIRST_OBSERVATION_BONUS = "FIRST_OBSERVATION_BONUS"
    COSMETIC_PURCHASE = "COSMETIC_PURCHASE"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class ReputationRank(StrEnum):
    OBSERVER = "OBSERVER"
    EXPLORER = "EXPLORER"
    RECORDER = "RECORDER"
    VERIFIER = "VERIFIER"
    ARCHIVIST = "ARCHIVIST"
    DODO_RANGER = "DODO_RANGER"


class AuditAction(StrEnum):
    MODERATION_DECISION = "MODERATION_DECISION"
    VERIFICATION_STATUS_CHANGED = "VERIFICATION_STATUS_CHANGED"
    EVIDENCE_ACCESSED = "EVIDENCE_ACCESSED"
    EVIDENCE_DELETED = "EVIDENCE_DELETED"
    COMPANY_CORRECTION = "COMPANY_CORRECTION"
    COMPANY_CLAIM_DECISION = "COMPANY_CLAIM_DECISION"
    USER_SANCTION = "USER_SANCTION"
    METRIC_RECOMPUTED = "METRIC_RECOMPUTED"
    COMPANY_ADD_REQUEST_DECISION = "COMPANY_ADD_REQUEST_DECISION"
