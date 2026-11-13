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
import re
from collections.abc import Iterator, Sequence
from pathlib import Path

from app.modules.companies.directory import DirectoryRecord, size_band_from_headcount

SOURCE = "NPS"

# Header aliases seen across data.go.kr releases.
_NAME_COLUMNS = ("사업장명", "사업장명칭", "가입사업장명")
_HEADCOUNT_COLUMNS = ("가입자수", "가입자 수", "신규취득자수", "고지인원")
_INDUSTRY_COLUMNS = ("업종명", "사업장업종코드명", "업태명")
_REF_COLUMNS = ("사업장기호", "자료생성기준일자_사업장기호", "사업자등록번호")
_ADDRESS_COLUMNS = ("사업장도로명상세주소", "사업장지번상세주소", "주소")
# Matched by prefix: recent releases append the code legend to the header,
# e.g. "사업장가입상태코드 1 등록 2 탈퇴".
_STATUS_PREFIX = "사업장가입상태코드"
_FORM_PREFIX = "사업장형태구분코드"
# A contractor registers each construction site's day (일용) or regular (상용)
# labour as its own workplace: "세안이엔씨 /일용/삼성서울병원 리모델링공사",
# "대륭개발-(건설일용)충북혁신 B-9BL", "강산이앤에쓰-(현장)분당동 …".
# Public bodies do the same per programme: "화성시청/장애인 일자리 사업". In
# both the employer is the part before the marker or the slash. A delimiter
# is required in front of the marker so a company that is actually called
# 일용-something keeps its name.
_SITE_MARKER = re.compile(
    r"\s*[-/(（\[]+\s*(?:건설)?(?:일용|상용|현장)직?(?:관리)?\s*[)）\]/-]*.*$"
)


def employer_name(workplace: str) -> str:
    """The employer behind an NPS workplace name."""
    name = _SITE_MARKER.sub("", workplace)
    name = name.split("/", 1)[0]
    # "마포구청(일반형일자리/전일제)" leaves "마포구청(일반형일자리": drop a
    # parenthetical the slash cut open.
    opened = name.count("(") + name.count("（")
    closed = name.count(")") + name.count("）")
    if opened > closed:
        name = re.split(r"[(（](?=[^(（]*$)", name)[0]
    return name.strip()


_WITHDRAWN = "2"  # 1 등록, 2 탈퇴
_SOLE_PROPRIETOR = "2"  # 1 법인, 2 개인


def _first(row: dict[str, str], columns: tuple[str, ...]) -> str | None:
    for column in columns:
        value = row.get(column)
        if value and value.strip():
            return value.strip()
    return None


def _column(fieldnames: Sequence[str] | None, prefix: str) -> str | None:
    return next((f for f in fieldnames or [] if f.strip().startswith(prefix)), None)


def parse(
    path: Path,
    *,
    encoding: str = "cp949",
    min_headcount: int = 0,
    include_sole_proprietors: bool = False,
) -> Iterator[DirectoryRecord]:
    """Streams records from an NPS workplace CSV.

    data.go.kr bulk files are usually CP949; pass `encoding="utf-8-sig"` for
    the UTF-8 exports. `min_headcount` filters out the long tail of tiny
    workplaces that are rarely what a jobseeker is searching for.

    Withdrawn workplaces (탈퇴) are always skipped: a closed employer is not
    somewhere anyone is applying. Sole proprietorships (개인) are skipped
    unless asked for, because their workplace name is often a person's name
    ("홍길동치과") — whether that may serve as company identity is with
    counsel (docs/legal/REVIEW_REQUEST.md Q8). Both filters apply only when
    the release carries the column.
    """
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        status_column = _column(reader.fieldnames, _STATUS_PREFIX)
        form_column = _column(reader.fieldnames, _FORM_PREFIX)
        for row in reader:
            name = _first(row, _NAME_COLUMNS)
            if name:
                name = employer_name(name)
            if not name:
                continue
            if status_column and (row.get(status_column) or "").strip() == _WITHDRAWN:
                continue
            if (
                not include_sole_proprietors
                and form_column
                and (row.get(form_column) or "").strip() == _SOLE_PROPRIETOR
            ):
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
