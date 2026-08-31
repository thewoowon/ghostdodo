"""Schemas shared across modules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page[T](BaseModel):
    """Cursor pagination. `next_cursor` is None on the last page."""

    items: list[T]
    next_cursor: str | None = None
