import type { Metadata } from "next";

import { CompanySearch } from "@/components/search/CompanySearch";
import { searchCompanies } from "@/lib/api/queries";
import { ApiUnavailableError } from "@/lib/api/client";
import { CompanyResultList } from "@/components/search/CompanyResultList";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "회사 검색",
  description: "회사별 채용 결과 통보율과 응답 기록을 검색하세요.",
  // Search result pages carry no unique content worth indexing.
  robots: { index: false, follow: true },
};

type Props = { searchParams: Promise<{ q?: string }> };

export default async function SearchPage({ searchParams }: Props) {
  const query = (await searchParams).q?.trim() ?? "";

  let results = null;
  let unavailable = false;
  if (query) {
    try {
      results = await searchCompanies(query);
    } catch (error) {
      if (error instanceof ApiUnavailableError) unavailable = true;
      else throw error;
    }
  }

  return (
    <div className={`gd-shell ${styles.page}`}>
      <h1 className={styles.title}>회사 검색</h1>
      <p className={styles.lede}>
        한글 회사명, 영문명, 이전 사명으로 찾을 수 있습니다.
      </p>

      <div className={styles.searchSlot}>
        <CompanySearch size="compact" initialQuery={query} autoFocus />
      </div>

      {unavailable ? (
        <p className={styles.notice}>
          지금은 검색을 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.
        </p>
      ) : results ? (
        <CompanyResultList companies={results} query={query} />
      ) : (
        <p className={styles.notice}>검색어를 입력하면 결과가 표시됩니다.</p>
      )}
    </div>
  );
}
