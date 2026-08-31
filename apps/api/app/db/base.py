"""SQLAlchemy declarative base and shared column conventions."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import ENUM as PostgresEnum  # noqa: N811
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming so Alembic autogenerate produces stable, reviewable names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UUIDPrimaryKey:
    """Public identifiers are UUIDs — never sequential ints (docs/05 §3),
    so a company page URL leaks no volume information."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def domain_enum[E: PyEnum](enum_cls: type[E], name: str) -> PostgresEnum:
    """Postgres enum column bound to an enum in `app.shared.enums`.

    Two things matter here and both are easy to get wrong:

    * `values_callable` persists member VALUES, not member names. Without it
      SQLAlchemy sends `W6M` where the database type holds `6m` — silently
      fine for every enum whose name equals its value, and a runtime error
      for the ones where it does not.
    * `create_type=False` because the types are created once, explicitly, in
      the `0001_bootstrap` migration.
    """
    return PostgresEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda e: [m.value for m in e],
    )
