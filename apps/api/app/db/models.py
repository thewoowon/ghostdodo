"""Single import surface for every ORM model.

Alembic autogenerate and `Base.metadata` both need every mapper imported.
Importing a model from anywhere else is fine; this module exists so nothing
is silently missing from a migration.
"""

from __future__ import annotations

from app.db.base import Base
from app.modules.community.models import (
    CommunityComment,
    CommunityPost,
    ContentReport,
    HelpfulVote,
    UserFollow,
)
from app.modules.companies.models import Company, CompanyAddRequest
from app.modules.company_claims.models import CompanyClaim, CompanyStatement, CorrectionRequest
from app.modules.evidence.models import Evidence, EvidenceAccessLog
from app.modules.jobs.models import JobPosting, OutboundClick
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.reports.models import RecruitmentExperience, RecruitmentStageEvent
from app.modules.reputation.models import CreditLedger, ReputationEvent, UserBadge
from app.modules.users.models import MagicLinkToken, SavedCompany, User
from app.modules.verification.models import AuditLog, VerificationReview

__all__ = [
    "AuditLog",
    "Base",
    "CommunityComment",
    "CommunityPost",
    "Company",
    "CompanyAddRequest",
    "CompanyClaim",
    "CompanyMetricSnapshot",
    "CompanyStatement",
    "ContentReport",
    "CorrectionRequest",
    "CreditLedger",
    "Evidence",
    "EvidenceAccessLog",
    "HelpfulVote",
    "JobPosting",
    "MagicLinkToken",
    "OutboundClick",
    "RecruitmentExperience",
    "RecruitmentStageEvent",
    "ReputationEvent",
    "SavedCompany",
    "User",
    "UserBadge",
    "UserFollow",
    "VerificationReview",
]
