"""금융감독원 DART OpenAPI — corpCode.

`GET https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key=...` returns a ZIP
containing CORPCODE.xml: every corporation registered with DART, with its
고유번호, 정식명칭, and 종목코드 where listed.

Accurate official names, but coverage is reporting entities — listed
companies plus filers. Pair it with the NPS source for smaller private
employers.

Requires a free API key from https://opendart.fss.or.kr.
"""

from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx

# defusedxml, not the stdlib parser: this XML arrives over the network, and
# the stdlib parser will resolve external entities.
from defusedxml import ElementTree

from app.modules.companies.directory import DirectoryRecord

SOURCE = "DART"
CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"


async def download_corp_code(api_key: str, destination: Path) -> Path:
    """Fetches the ZIP and extracts CORPCODE.xml. It is a single large file,
    so it is cached on disk rather than re-fetched per run."""
    await asyncio.to_thread(destination.parent.mkdir, parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(CORP_CODE_URL, params={"crtfc_key": api_key})
        response.raise_for_status()

    # An auth failure comes back as XML, not a ZIP, so check before unzipping.
    if not response.content.startswith(b"PK"):
        raise RuntimeError(
            "DART returned a non-ZIP response — check crtfc_key. "
            f"Body starts: {response.content[:200]!r}"
        )

    def _extract() -> None:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            name = next(n for n in archive.namelist() if n.upper().endswith("CORPCODE.XML"))
            destination.write_bytes(archive.read(name))

    # Unzipping and writing several MB would block the loop; this runs once
    # from the CLI, but keeping it off the loop costs nothing.
    await asyncio.to_thread(_extract)
    return destination


def parse(path: Path, *, listed_only: bool = False) -> Iterator[DirectoryRecord]:
    """Streams records from CORPCODE.xml.

    `listed_only` keeps just companies with a 종목코드 — a much smaller, higher
    signal set that is useful for a first import.
    """
    root = ElementTree.parse(path).getroot()
    if root is None:
        return
    for element in root.iter("list"):
        corp_code = (element.findtext("corp_code") or "").strip()
        corp_name = (element.findtext("corp_name") or "").strip()
        stock_code = (element.findtext("stock_code") or "").strip()

        if not corp_code or not corp_name:
            continue
        if listed_only and not stock_code:
            continue

        extra = [stock_code] if stock_code else []
        yield DirectoryRecord(
            source=SOURCE,
            source_ref=corp_code,
            legal_name=corp_name,
            extra_aliases=extra,
        )
