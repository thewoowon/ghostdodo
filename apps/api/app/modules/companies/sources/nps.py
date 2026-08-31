"""국민연금공단 — 국민연금 가입 사업장 내역 (공공데이터포털).

Every workplace with National Pension enrollment: 3+ members for 법인, and
10+ for 개인사업장. That makes it the broadest lawful source of Korean
employer names, and it is the one that covers the startups and mid-size
companies people actually apply to and that DART does not list.

The subscriber count doubles as a headcount proxy for the size band.

Distributed as bulk CSV (and an API) from data.go.kr. Column names have
varied between releases, so the parser matches on several known headers
rather than a single fixed layout.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from app.modules.companies.directory import DirectoryRecord, size_band_from_headcount

SOURCE = "NPS"

# Header aliases seen across data.go.kr releases.
_NAME_COLUMNS = ("사업장명", "사업장명칭", "가입사업장명")
_HEADCOUNT_COLUMNS = ("가입자수", "가입자 수", "신규취득자수", "고지인원")
_INDUSTRY_COLUMNS = ("업종명", "사업장업종코드명", "업태명")
_REF_COLUMNS = ("사업장기호", "자료생성기준일자_사업장기호", "사업자등록번호")
_ADDRESS_COLUMNS = ("사업장도로명상세주소", "사업장지번상세주소", "주소")


def _first(row: dict[str, str], columns: tuple[str, ...]) -> str | None:
    for column in columns:
        value = row.get(column)
        if value and value.strip():
            return value.strip()
    return None


def parse(
    path: Path, *, encoding: str = "cp949", min_headcount: int = 0
) -> Iterator[DirectoryRecord]:
    """Streams records from an NPS workplace CSV.

    data.go.kr bulk files are usually CP949; pass `encoding="utf-8-sig"` for
    the UTF-8 exports. `min_headcount` filters out the long tail of tiny
    workplaces that are rarely what a jobseeker is searching for.
    """
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            name = _first(row, _NAME_COLUMNS)
            if not name:
                continue

            raw_count = _first(row, _HEADCOUNT_COLUMNS)
            try:
                headcount = int(float(raw_count)) if raw_count else None
            except ValueError:
                headcount = None

            if min_headcount and (headcount or 0) < min_headcount:
                continue

            # No stable primary key in every release; fall back to the name so
            # re-imports still match the same row.
            ref = _first(row, _REF_COLUMNS) or name

            yield DirectoryRecord(
                source=SOURCE,
                source_ref=ref[:64],
                legal_name=name,
                industry=_first(row, _INDUSTRY_COLUMNS),
                size_band=size_band_from_headcount(headcount),
            )


def address_of(row: dict[str, str]) -> str | None:
    """Exposed for future location filtering; not imported today because the
    directory does not publish company addresses."""
    return _first(row, _ADDRESS_COLUMNS)
