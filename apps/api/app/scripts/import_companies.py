"""Import company directory metadata from a lawful public registry.

    # DART — official names for listed and reporting companies
    export DART_API_KEY=...
    uv run python -m app.scripts.import_companies dart --listed-only

    # 국민연금 — broad coverage including private employers
    uv run python -m app.scripts.import_companies nps ~/Downloads/nps.csv \
        --min-headcount 20

This imports IDENTITY ONLY. No report, snapshot, or ledger row is written,
so every imported company starts at zero observations and reads `표본 부족`
until real applicants file qualified reports.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from app.core.logging import configure_logging
from app.db.session import db_session, dispose_engine
from app.modules.companies.directory import DirectoryRecord, import_records
from app.modules.companies.sources import dart, nps

CACHE_DIR = Path(".cache")


async def _run(records: list[DirectoryRecord], *, dry_run: bool) -> None:
    print(f"parsed {len(records)} records")
    if not records:
        return

    print("sample:")
    for record in records[:5]:
        print(f"  {record.legal_name}  ({record.source}:{record.source_ref})")

    if dry_run:
        print("\n--dry-run: nothing written")
        return

    async with db_session() as session:
        stats = await import_records(session, records)
    print(f"\n{stats}")
    print("note: identity only — no metrics were created for these companies")
    await dispose_engine()


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="parse but do not write")
    parser.add_argument("--limit", type=int, default=0, help="import at most N records")
    sub = parser.add_subparsers(dest="source", required=True)

    dart_parser = sub.add_parser("dart", help="금융감독원 DART corpCode")
    dart_parser.add_argument(
        "file", nargs="?", type=Path, help="CORPCODE.xml (downloaded if omitted)"
    )
    dart_parser.add_argument(
        "--listed-only",
        action="store_true",
        help="only companies with a 종목코드 — smaller, higher signal",
    )

    nps_parser = sub.add_parser("nps", help="국민연금 가입 사업장 내역 CSV")
    nps_parser.add_argument("file", type=Path)
    nps_parser.add_argument("--encoding", default="cp949")
    nps_parser.add_argument(
        "--min-headcount",
        type=int,
        default=0,
        help="skip workplaces below this subscriber count",
    )

    args = parser.parse_args()
    configure_logging("INFO", json_output=False)

    if args.source == "dart":
        path = args.file
        if path is None:
            api_key = os.environ.get("DART_API_KEY")
            if not api_key:
                print(
                    "DART_API_KEY is not set. Get a free key at "
                    "https://opendart.fss.or.kr, or pass a CORPCODE.xml path.",
                    file=sys.stderr,
                )
                return 1
            path = CACHE_DIR / "CORPCODE.xml"
            if not path.exists():
                print("downloading corpCode.xml from DART…")
                await dart.download_corp_code(api_key, path)
        records = list(dart.parse(path, listed_only=args.listed_only))
    else:
        if not args.file.exists():
            print(f"no such file: {args.file}", file=sys.stderr)
            return 1
        records = list(
            nps.parse(args.file, encoding=args.encoding, min_headcount=args.min_headcount)
        )

    if args.limit:
        records = records[: args.limit]

    await _run(records, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
