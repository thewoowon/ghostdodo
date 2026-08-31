"""Directory import rules.

The load-bearing assertion here is the last class: importing a company name
must never create a metric. Registry data establishes that an employer
exists; only qualified applicant reports establish how it behaves.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.db.session import SessionLocal
from app.modules.companies.directory import (
    DirectoryRecord,
    import_records,
    size_band_from_headcount,
)
from app.modules.companies.models import Company
from app.modules.companies.normalize import (
    display_name,
    generate_aliases,
    match_key,
    slugify,
    strip_legal_form,
)
from app.modules.companies.service import search_companies
from app.modules.companies.sources import dart, nps
from app.modules.metrics.models import CompanyMetricSnapshot
from app.modules.reports.models import RecruitmentExperience
from app.shared.enums import CompanySizeBand
from sqlalchemy import func, select


class TestNormalization:
    @pytest.mark.parametrize(
        "raw",
        ["주식회사 카카오", "(주)카카오", "카카오(주)", "카카오", "카카오 주식회사"],
    )
    def test_legal_forms_collapse_to_one_key(self, raw: str) -> None:
        """All five spellings must dedupe to a single company — otherwise the
        observations split and every fragment stays under the sample bar."""
        assert match_key(raw) == "카카오"

    def test_english_legal_forms_are_stripped(self) -> None:
        assert strip_legal_form("DodoLab Inc.") == "DodoLab"
        assert strip_legal_form("Kakao Corp") == "Kakao"

    def test_display_name_drops_the_legal_form(self) -> None:
        assert display_name("주식회사 도도랩") == "도도랩"

    def test_display_name_falls_back_when_nothing_remains(self) -> None:
        # A company literally named 주식회사 must not become an empty string.
        assert display_name("주식회사") == "주식회사"

    def test_full_width_characters_normalize(self) -> None:
        assert match_key("ＫＡＫＡＯ") == match_key("KAKAO")

    def test_aliases_cover_the_forms_users_type(self) -> None:
        aliases = generate_aliases("주식회사 도도랩", "DodoLab Inc.")
        assert "도도랩" in aliases
        assert "(주)도도랩" in aliases
        assert "주식회사 도도랩" in aliases
        assert "DodoLab" in aliases

    def test_slug_keeps_korean_and_has_a_fallback(self) -> None:
        assert slugify("주식회사 도도랩", fallback="x") == "도도랩"
        assert slugify("Kakao Corp.", fallback="x") == "kakao"
        assert slugify("!!!", fallback="co-123") == "co-123"


class TestSizeBands:
    @pytest.mark.parametrize(
        ("count", "expected"),
        [
            (None, CompanySizeBand.UNKNOWN),
            (0, CompanySizeBand.UNKNOWN),
            (9, CompanySizeBand.B1_9),
            (49, CompanySizeBand.B10_49),
            (199, CompanySizeBand.B50_199),
            (999, CompanySizeBand.B200_999),
            (1000, CompanySizeBand.B1000_PLUS),
        ],
    )
    def test_boundaries(self, count: int | None, expected: CompanySizeBand) -> None:
        assert size_band_from_headcount(count) is expected


class TestSourceParsers:
    def test_dart_parses_corpcode_xml(self, tmp_path: Path) -> None:
        xml = tmp_path / "CORPCODE.xml"
        xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
            <result>
              <list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name>
                <stock_code>005930</stock_code><modify_date>20260101</modify_date></list>
              <list><corp_code>00164742</corp_code><corp_name>주식회사 도도랩테스트</corp_name>
                <stock_code></stock_code><modify_date>20260101</modify_date></list>
              <list><corp_code></corp_code><corp_name></corp_name>
                <stock_code></stock_code><modify_date></modify_date></list>
            </result>""",
            encoding="utf-8",
        )
        records = list(dart.parse(xml))
        assert len(records) == 2  # the empty row is skipped
        assert records[0].legal_name == "삼성전자"
        # The ticker becomes a searchable alias.
        assert "005930" in records[0].extra_aliases

    def test_dart_listed_only_filter(self, tmp_path: Path) -> None:
        xml = tmp_path / "CORPCODE.xml"
        xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
            <result>
              <list><corp_code>1</corp_code><corp_name>상장사</corp_name>
                <stock_code>005930</stock_code></list>
              <list><corp_code>2</corp_code><corp_name>비상장사</corp_name>
                <stock_code></stock_code></list>
            </result>""",
            encoding="utf-8",
        )
        records = list(dart.parse(xml, listed_only=True))
        assert [r.legal_name for r in records] == ["상장사"]

    def test_nps_parses_csv_and_derives_size_band(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "nps.csv"
        csv_path.write_text(
            "사업장명,가입자수,업종명,사업장기호\n"
            "주식회사 도도랩테스트,120,소프트웨어 개발업,12345\n"
            "작은가게,2,음식점업,67890\n",
            encoding="utf-8-sig",
        )
        records = list(nps.parse(csv_path, encoding="utf-8-sig"))
        assert len(records) == 2
        assert records[0].size_band is CompanySizeBand.B50_199
        assert records[0].industry == "소프트웨어 개발업"

    def test_nps_min_headcount_filters_the_long_tail(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "nps.csv"
        csv_path.write_text("사업장명,가입자수\n큰회사,300\n작은가게,2\n", encoding="utf-8-sig")
        records = list(nps.parse(csv_path, encoding="utf-8-sig", min_headcount=20))
        assert [r.legal_name for r in records] == ["큰회사"]

    def test_nps_tolerates_alternate_column_names(self, tmp_path: Path) -> None:
        """Header names have varied between data.go.kr releases."""
        csv_path = tmp_path / "nps.csv"
        csv_path.write_text(
            "사업장명칭,가입자 수,업태명\n대체표기회사,80,제조업\n", encoding="utf-8-sig"
        )
        records = list(nps.parse(csv_path, encoding="utf-8-sig"))
        assert records[0].legal_name == "대체표기회사"
        assert records[0].size_band is CompanySizeBand.B50_199


def _record(name: str, **kwargs: object) -> DirectoryRecord:
    return DirectoryRecord(
        source="TEST",
        source_ref=f"ref-{name}",
        legal_name=name,
        **kwargs,  # type: ignore[arg-type]
    )


class TestImport:
    async def test_variant_spellings_merge_into_one_company(self, fresh_db: None) -> None:
        names = ["주식회사 임포트테스트", "(주)임포트테스트", "임포트테스트"]
        try:
            async with SessionLocal() as session:
                stats = await import_records(session, [_record(n) for n in names])
                assert stats.created == 1
                assert stats.updated == 2

                count = (
                    await session.execute(
                        select(func.count(Company.id)).where(
                            Company.match_key == match_key(names[0])
                        )
                    )
                ).scalar_one()
                assert count == 1
        finally:
            await _cleanup("임포트테스트")

    async def test_imported_company_is_searchable_by_every_spelling(self, fresh_db: None) -> None:
        try:
            async with SessionLocal() as session:
                await import_records(
                    session, [_record("주식회사 검색표기테스트", name_en="SpellingTest")]
                )

            async with SessionLocal() as session:
                for query in ["검색표기테스트", "(주)검색표기테스트", "SpellingTest"]:
                    found = await search_companies(session, query=query)
                    assert any("검색표기테스트" in c.display_name_ko for c in found), query
        finally:
            await _cleanup("검색표기테스트")

    async def test_demo_fixtures_are_never_overwritten_by_an_import(self, fresh_db: None) -> None:
        """A name collision must not quietly promote a fictional company into
        a real one, or hand it a real registry identity."""
        async with SessionLocal() as session:
            demo = Company(
                slug="collision-demo-co",
                legal_name_ko="충돌데모회사",
                display_name_ko="충돌데모회사",
                aliases=["충돌데모회사"],
                is_demo=True,
                match_key=match_key("충돌데모회사"),
            )
            session.add(demo)
            await session.commit()

        try:
            async with SessionLocal() as session:
                stats = await import_records(session, [_record("주식회사 충돌데모회사")])
                assert stats.skipped == 1
                assert stats.updated == 0

            async with SessionLocal() as session:
                kept = (
                    await session.execute(
                        select(Company).where(Company.slug == "collision-demo-co")
                    )
                ).scalar_one()
                assert kept.is_demo is True
                assert kept.directory_source is None
        finally:
            await _cleanup("충돌데모회사")

    async def test_slug_collisions_get_a_suffix(self, fresh_db: None) -> None:
        try:
            async with SessionLocal() as session:
                # Same display name, different legal names -> different keys.
                await import_records(
                    session,
                    [_record("슬러그충돌 주식회사"), _record("슬러그충돌 유한회사")],
                )

            async with SessionLocal() as session:
                rows = (
                    (
                        await session.execute(
                            select(Company.slug).where(Company.legal_name_ko.like("슬러그충돌%"))
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(rows) == len(set(rows)), "slugs must be unique"
        finally:
            await _cleanup("슬러그충돌")


class TestImportCreatesNoMetrics:
    """The rule that keeps the product honest."""

    async def test_import_writes_no_reports_or_snapshots(self, fresh_db: None) -> None:
        try:
            async with SessionLocal() as session:
                before_reports = (
                    await session.execute(select(func.count(RecruitmentExperience.id)))
                ).scalar_one()
                before_snapshots = (
                    await session.execute(select(func.count(CompanyMetricSnapshot.id)))
                ).scalar_one()

                await import_records(
                    session,
                    [_record(f"지표없음테스트{i}") for i in range(5)],
                )

                after_reports = (
                    await session.execute(select(func.count(RecruitmentExperience.id)))
                ).scalar_one()
                after_snapshots = (
                    await session.execute(select(func.count(CompanyMetricSnapshot.id)))
                ).scalar_one()

                assert after_reports == before_reports
                assert after_snapshots == before_snapshots

                # And the companies exist with an explicitly empty record count.
                companies = (
                    (
                        await session.execute(
                            select(Company).where(Company.legal_name_ko.like("지표없음테스트%"))
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(companies) == 5
                assert all(c.public_report_count == 0 for c in companies)
                assert all(not c.is_demo for c in companies)
        finally:
            await _cleanup("지표없음테스트")


async def _cleanup(name_prefix: str) -> None:
    from sqlalchemy import delete

    async with SessionLocal() as session:
        await session.execute(delete(Company).where(Company.legal_name_ko.like(f"%{name_prefix}%")))
        await session.commit()
