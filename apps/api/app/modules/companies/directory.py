"""Company directory import from lawful public registries.

What this module may and may not do is the whole point of it:

  * It MAY create and update company identity — names, aliases, industry,
    size band, website — from public registries.
  * It MAY NOT create, seed, or influence a single response metric. An
    imported company starts with zero reports and reads `표본 부족` until
    real applicants file qualified observations (docs/10 seed data rule).

Nothing here writes to reports, snapshots, or ledgers, and that separation
is asserted in tests.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.companies.models import Company
from app.modules.companies.normalize import (
    display_name,
    generate_aliases,
    match_key,
    slugify,
)
from app.shared.enums import CompanySizeBand

log = get_logger(__name__)


@dataclass(slots=True)
class DirectoryRecord:
    """One company as a registry describes it, before normalization."""

    source: str
    """Registry identifier, e.g. `DART` or `NPS`."""

    source_ref: str
    """Stable id within that registry — DART 고유번호, NPS 사업장기호."""

    legal_name: str
    name_en: str | None = None
    industry: str | None = None
    website: str | None = None
    size_band: CompanySizeBand = CompanySizeBand.UNKNOWN
    extra_aliases: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ImportStats:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    def __str__(self) -> str:
        return f"created={self.created} updated={self.updated} skipped={self.skipped}"


def size_band_from_headcount(count: int | None) -> CompanySizeBand:
    """Maps an employee count (NPS subscriber count is a good proxy) onto the
    published band. Bands rather than exact counts: the registry figure is a
    snapshot and precision would imply accuracy it does not have."""
    if count is None or count <= 0:
        return CompanySizeBand.UNKNOWN
    if count < 10:
        return CompanySizeBand.B1_9
    if count < 50:
        return CompanySizeBand.B10_49
    if count < 200:
        return CompanySizeBand.B50_199
    if count < 1000:
        return CompanySizeBand.B200_999
    return CompanySizeBand.B1000_PLUS


async def _unique_slug(session: AsyncSession, base: str) -> str:
    """Slugs are public URLs, so collisions get a short deterministic suffix
    rather than a rename that would break an existing link."""
    candidate = base
    for attempt in range(50):
        exists = (
            await session.execute(select(Company.id).where(Company.slug == candidate))
        ).first()
        if exists is None:
            return candidate
        candidate = f"{base}-{attempt + 2}"
    return f"{base}-{uuid.uuid4().hex[:6]}"


async def upsert_record(
    session: AsyncSession, record: DirectoryRecord, *, now: datetime | None = None
) -> str:
    """Create or update one company. Returns 'created' | 'updated' | 'skipped'."""
    now = now or datetime.now(UTC)
    key = match_key(record.legal_name)
    if not key:
        return "skipped"

    existing = (
        await session.execute(select(Company).where(Company.match_key == key))
    ).scalar_one_or_none()

    aliases = generate_aliases(record.legal_name, record.name_en, *record.extra_aliases)

    if existing is None:
        base_slug = slugify(record.legal_name, fallback=f"co-{key[:12]}")
        company = Company(
            slug=await _unique_slug(session, base_slug),
            legal_name_ko=record.legal_name[:200],
            display_name_ko=display_name(record.legal_name)[:200],
            name_en=record.name_en[:200] if record.name_en else None,
            aliases=aliases,
            industry=record.industry,
            website=record.website,
            size_band=record.size_band,
            match_key=key,
            directory_source=record.source,
            directory_ref=record.source_ref,
            directory_synced_at=now,
            # Imported identity only. No reports, no metrics.
            is_demo=False,
            public_report_count=0,
        )
        session.add(company)
        # Flush immediately: the session has autoflush off, so without this a
        # second record for the same company later in the batch would not see
        # the pending row and would try to create a duplicate. Registries
        # routinely list one employer several times — NPS has a row per
        # workplace — so this is the common case, not an edge case.
        await session.flush()
        return "created"

    # A demo fixture must never be silently promoted into a real company by a
    # name collision.
    if existing.is_demo:
        return "skipped"

    merged = list(dict.fromkeys([*existing.aliases, *aliases]))
    existing.aliases = merged
    existing.legal_name_ko = record.legal_name[:200]
    existing.display_name_ko = display_name(record.legal_name)[:200]
    if record.name_en:
        existing.name_en = record.name_en[:200]
    if record.industry:
        existing.industry = record.industry
    if record.website:
        existing.website = record.website
    if record.size_band is not CompanySizeBand.UNKNOWN:
        existing.size_band = record.size_band
    existing.directory_source = record.source
    existing.directory_ref = record.source_ref
    existing.directory_synced_at = now
    return "updated"


async def import_records(
    session: AsyncSession,
    records: list[DirectoryRecord],
    *,
    batch_size: int = 500,
) -> ImportStats:
    """Imports a batch of registry records, committing periodically so a large
    import can be resumed rather than restarted."""
    stats = ImportStats()
    now = datetime.now(UTC)

    for index, record in enumerate(records, start=1):
        outcome = await upsert_record(session, record, now=now)
        setattr(stats, outcome, getattr(stats, outcome) + 1)

        if index % batch_size == 0:
            await session.commit()
            log.info("directory.import.progress", processed=index, stats=str(stats))

    await session.commit()
    log.info("directory.import.done", stats=str(stats))
    return stats
