"""S3-compatible object storage for evidence.

Every object lives in a private bucket. The only ways bytes leave are a
short-lived signed PUT for the uploader and a short-lived signed GET for a
moderator — both time-boxed, and the GET is always audit-logged by the
caller in `service.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import aioboto3
from botocore.config import Config

from app.core.config import settings

_session = aioboto3.Session()


def _client_kwargs() -> dict[str, Any]:
    return {
        "endpoint_url": settings.s3_endpoint,
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"},
        ),
    }


def build_object_key(experience_id: uuid.UUID, evidence_id: uuid.UUID, ext: str) -> str:
    """Date-partitioned, unguessable key. The key alone is not a capability —
    the bucket is private — but it should not encode anything about the user."""
    today = datetime.now(UTC)
    safe_ext = ext.lower().lstrip(".")[:8] or "bin"
    return f"evidence/{today:%Y/%m}/{experience_id}/{evidence_id}.{safe_ext}"


async def create_upload_url(
    object_key: str, *, content_type: str, max_bytes: int
) -> Mapping[str, Any]:
    """Presigned POST, which lets the storage layer enforce the size limit
    server-side rather than trusting the client to respect it."""
    async with _session.client("s3", **_client_kwargs()) as s3:
        return await s3.generate_presigned_post(
            Bucket=settings.s3_bucket,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=settings.evidence_upload_url_ttl_seconds,
        )


async def create_moderator_read_url(object_key: str) -> str:
    """Short-lived read URL. Callers must record an EvidenceAccessLog entry."""
    async with _session.client("s3", **_client_kwargs()) as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": object_key},
            ExpiresIn=settings.evidence_moderator_url_ttl_seconds,
        )


async def head_object(object_key: str) -> Mapping[str, Any] | None:
    """Confirms an upload actually landed, and reports its true size/type —
    the client's claim about either is not trusted."""
    async with _session.client("s3", **_client_kwargs()) as s3:
        try:
            return await s3.head_object(Bucket=settings.s3_bucket, Key=object_key)
        except Exception:
            return None


async def delete_object(object_key: str) -> None:
    async with _session.client("s3", **_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.s3_bucket, Key=object_key)
