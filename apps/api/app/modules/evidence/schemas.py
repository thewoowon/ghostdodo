from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.enums import EvidenceAccessState, EvidenceReviewState
from app.shared.schemas import ORMModel

# Screenshots of result emails and job-board status pages. No archives, no
# documents that can carry macros.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/png", "image/jpeg", "image/webp", "application/pdf"}
)

_EXTENSION_BY_TYPE: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


def extension_for(content_type: str) -> str:
    return _EXTENSION_BY_TYPE.get(content_type, "bin")


class UploadIntentInput(BaseModel):
    content_type: str
    size_bytes: int = Field(gt=0)
    kind: str = Field(default="OTHER", max_length=40)
    original_filename: str | None = Field(default=None, max_length=255)


class UploadIntentOutput(BaseModel):
    """Carries the presigned POST target — but never the bucket key itself in
    a form the client could reuse for reads."""

    evidence_id: uuid.UUID
    upload_url: str
    fields: dict[str, Any]
    expires_in_seconds: int


class EvidenceCompleteInput(BaseModel):
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class EvidenceSummary(ORMModel):
    """The owner's view of their own attachment.

    Note what is absent: `object_key`. Public and owner-facing serializers
    have no field for it, so it cannot leak through this path
    (specs/API_CONTRACT.md).
    """

    id: uuid.UUID
    kind: str
    content_type: str
    size_bytes: int | None
    original_filename: str | None
    review_state: EvidenceReviewState
    access_state: EvidenceAccessState
    created_at: datetime


class ModeratorEvidenceView(EvidenceSummary):
    """Moderator-only. The signed URL expires in minutes and every issuance
    is written to `evidence_access_logs`."""

    signed_url: str
    signed_url_expires_in_seconds: int
