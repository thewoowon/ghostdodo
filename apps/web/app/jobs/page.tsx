import type { Metadata } from "next";
import Link from "next/link";

import { DodoEgg, RadarRipple } from "@/components/brand/svg/marks";
import { JobCardList } from "@/components/jobs/JobCardList";
import { load } from "@/lib/api/load";
import { getJobs } from "@/lib/api/queries";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "채용공고",
  description:
    "지원하기 전에 그 회사가 답은 해주는지 먼저 확인하세요. 공고마다 회사의 응답 기록으로 이어집니다.",
  alternates: { canonical: "/jobs" },
};

type Props = {
  searchParams: Promise<{ q?: string; cursor?: string }>;
};

const PAGE_SIZE = 24;

export default async function JobsPage({ searchParams }: Props) {
  const { q, cursor } = await searchParams;
  const query = q?.trim() ?? "";

  const result = await load(() =>
    getJobs({
      ...(query ? { q: query } : {}),
      ...(cursor ? { cursor } : {}),
      limit: PAGE_SIZE,
    }),
  );

  if (!result.ok) {
    return (
      <div className={`gd-shell ${styles.errorState}`}>
        <DodoEgg size={34} className={styles.errorMark} />
        <h1 className={styles.errorTitle}>지금은 공고를 불러올 수 없습니다</h1>
        <p className={styles.errorBody}>
          {result.failure === "not-found"
            ? "채용공고는 아직 공개 준비 중입니다."
            : "일시적인 연결 문제입니다. 잠시 후 다시 시도해 주세요."}
        </p>
      </div>
    );
  }

  const { items, next_cursor: nextCursor } = result.data;

  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>채용공고</h1>
        <p className={styles.lede}>
          고스트도도는 지원서를 대신 받지 않습니다. 모든 공고는 회사나 채용
          사이트로 바로 연결되고, 공고 옆에는 그 회사의 응답 기록이 함께
          있습니다.
        </p>
      </header>

      <form className={styles.search} action="/jobs" method="get" role="search">
        <label htmlFor="jobs-q" className="gd-sr-only">
          공고 검색
        </label>
        <RadarRipple size={20} className={styles.searchMark} aria-hidden />
        <input
          id="jobs-q"
          name="q"
          type="search"
          defaultValue={query}
          placeholder="직무, 지역, 회사명"
          className={styles.searchInput}
          maxLength={100}
        />
        <button type="submit" className={styles.searchSubmit}>
          검색
        </button>
      </form>

      {query && (
        <p className={styles.resultNote}>
          <strong>{query}</strong> 검색 결과{" "}
          <span className="gd-tabular">{items.length}건</span>
          {" · "}
          <Link href="/jobs" className={styles.resetLink}>
            전체 공고 보기
          </Link>
        </p>
      )}

      <JobCardList
        jobs={items}
        emptyBody={
          query
            ? "검색어와 맞는 공고를 찾지 못했습니다. 회사명을 직접 검색해 보세요."
            : "마감되지 않은 공고만 이곳에 표시됩니다."
        }
      />

      {nextCursor && (
        <div className={styles.more}>
          <Link
            href={`/jobs?${new URLSearchParams({
              ...(query ? { q: query } : {}),
              cursor: nextCursor,
            })}`}
            className={styles.moreLink}
          >
            다음 공고 보기
          </Link>
        </div>
      )}
    </div>
  );
}
