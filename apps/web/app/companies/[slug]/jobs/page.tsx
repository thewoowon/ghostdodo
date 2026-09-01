import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DodoEgg } from "@/components/brand/svg/marks";
import { JobCardList } from "@/components/jobs/JobCardList";
import { load } from "@/lib/api/load";
import { getCompany, getCompanyJobs } from "@/lib/api/queries";
import { decodeRouteParam } from "@/lib/route-params";

import styles from "./page.module.css";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ cursor?: string }>;
};

const PAGE_SIZE = 24;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = decodeRouteParam((await params).slug);
  try {
    const company = await getCompany(slug);
    return {
      title: `${company.display_name_ko} 채용공고`,
      description: `${company.display_name_ko}의 현재 채용공고와 채용 응답 기록을 함께 확인하세요.`,
      alternates: { canonical: `/companies/${company.slug}/jobs` },
    };
  } catch {
    return { title: "회사를 찾을 수 없습니다" };
  }
}

export default async function CompanyJobsPage({ params, searchParams }: Props) {
  const slug = decodeRouteParam((await params).slug);
  const { cursor } = await searchParams;

  const result = await load(() =>
    Promise.all([
      getCompany(slug),
      getCompanyJobs(slug, { ...(cursor ? { cursor } : {}), limit: PAGE_SIZE }),
    ]),
  );

  if (!result.ok) {
    if (result.failure === "not-found") notFound();
    return (
      <div className={`gd-shell ${styles.errorState}`}>
        <DodoEgg size={34} className={styles.errorMark} />
        <h1 className={styles.errorTitle}>지금은 공고를 불러올 수 없습니다</h1>
        <p className={styles.errorBody}>
          일시적인 연결 문제입니다. 잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  const [company, jobs] = result.data;

  return (
    <div className={`gd-shell ${styles.page}`}>
      <nav className={styles.breadcrumb} aria-label="위치">
        <Link href={`/companies/${company.slug}`} className={styles.breadcrumbLink}>
          {company.display_name_ko}
        </Link>
        <span aria-hidden>/</span>
        <span>채용공고</span>
      </nav>

      <header className={styles.header}>
        <h1 className={styles.title}>
          {company.display_name_ko} 채용공고
          {company.is_demo && <span className={styles.demoTag}>샘플 데이터</span>}
        </h1>
        <p className={styles.lede}>
          공고는 이 회사가 채용 중이라는 사실만 말합니다. 이 회사가 결과를
          통보하는지는{" "}
          <Link href={`/companies/${company.slug}`} className={styles.inlineLink}>
            응답 기록
          </Link>
          에서 확인하세요.
        </p>
      </header>

      <JobCardList
        jobs={jobs.items}
        showCompany={false}
        emptyBody="마감되지 않은 공고만 이곳에 표시됩니다."
      />

      {jobs.next_cursor && (
        <div className={styles.more}>
          <Link
            href={`/companies/${company.slug}/jobs?${new URLSearchParams({
              cursor: jobs.next_cursor,
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
