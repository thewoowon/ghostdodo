import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  DodoEgg,
  FieldNotebook,
  FootprintMark,
  TimelineBone,
} from "@/components/brand/svg/marks";
import { CorrectionForm } from "@/components/company/CorrectionForm";
import { MetricCard } from "@/components/company/MetricCard";
import { StageBreakdown } from "@/components/company/StageBreakdown";
import { ReportCardList } from "@/components/company/ReportCardList";
import { VerdictBadge } from "@/components/company/VerdictBadge";
import { JobCardList } from "@/components/jobs/JobCardList";
import { decodeRouteParam } from "@/lib/route-params";
import { load } from "@/lib/api/load";
import {
  getCompany,
  getCompanyJobs,
  getCompanyMetrics,
  getCompanyReports,
} from "@/lib/api/queries";
import type { MetricWindow } from "@/lib/domain";
import { WINDOW_LABELS } from "@/lib/domain";
import {
  ELIGIBILITY_LABELS,
  ELIGIBILITY_NOTES,
  formatDays,
  formatRate,
  responseVerdict,
} from "@/lib/format/metrics";

import styles from "./page.module.css";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ window?: string }>;
};

const WINDOWS: MetricWindow[] = ["6m", "12m", "all"];

function parseWindow(value: string | undefined): MetricWindow {
  return WINDOWS.includes(value as MetricWindow) ? (value as MetricWindow) : "12m";
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = decodeRouteParam((await params).slug);
  try {
    const company = await getCompany(slug);
    return {
      title: `${company.display_name_ko} 채용 응답 기록`,
      description: `${company.display_name_ko}의 결과 통보율과 응답 시간을 지원자 기록으로 확인하세요.`,
      alternates: { canonical: `/companies/${company.slug}` },
      openGraph: {
        title: `${company.display_name_ko} — GhostDodo`,
        description: `${company.display_name_ko}의 채용 응답 기록`,
        url: `/companies/${company.slug}`,
      },
    };
  } catch {
    return { title: "회사를 찾을 수 없습니다" };
  }
}

export default async function CompanyPage({ params, searchParams }: Props) {
  const slug = decodeRouteParam((await params).slug);
  const window = parseWindow((await searchParams).window);

  // One round of parallel fetches — the page must not fan out per section
  // (docs/04 §6: no N+1 on the company page). Resolved to a value before any
  // JSX is constructed, since a render-time error would escape a try/catch.
  const result = await load(() =>
    Promise.all([
      getCompany(slug),
      getCompanyMetrics(slug, window),
      getCompanyReports(slug),
    ]),
  );

  if (!result.ok) {
    if (result.failure === "not-found") notFound();
    return (
      <div className={`gd-shell ${styles.errorState}`}>
        <DodoEgg size={34} className={styles.errorMark} />
        <h1 className={styles.errorTitle}>지금은 기록을 불러올 수 없습니다</h1>
        <p className={styles.errorBody}>
          일시적인 연결 문제입니다. 잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  const [company, metrics, reports] = result.data;

  // Fetched apart from the block above, and allowed to fail on its own: jobs
  // sit behind a feature flag, and a closed or unhealthy jobs surface must
  // not take down the page that holds the response record.
  const jobsResult = await load(() => getCompanyJobs(company.slug, { limit: 3 }));
  const jobs = jobsResult.ok ? jobsResult.data.items : [];

  const verdict = responseVerdict(metrics.response_rate, metrics.eligibility);
  const windowLabel = WINDOW_LABELS[window];

  return (
    <article className={`gd-shell ${styles.page}`}>
      <header className={styles.identity}>
        <div className={styles.identityMain}>
          <span className={styles.monogram} aria-hidden>
            {company.display_name_ko.slice(0, 1)}
          </span>
          <div>
            <h1 className={styles.name}>
              {company.display_name_ko}
              {company.is_demo && <span className={styles.demoTag}>샘플 데이터</span>}
            </h1>
            <p className={styles.meta}>
              {company.legal_name_ko}
              {company.name_en ? ` · ${company.name_en}` : ""}
              {company.industry ? ` · ${company.industry}` : ""}
            </p>
          </div>
        </div>
        <VerdictBadge verdict={verdict} />
      </header>

      {company.is_demo && (
        <p className={styles.demoNotice}>
          이 회사는 개발용 가상 회사입니다. 실제 기업의 채용 데이터가 아닙니다.
        </p>
      )}

      <nav className={styles.windowTabs} aria-label="집계 기간">
        {WINDOWS.map((w) => (
          <Link
            key={w}
            href={`/companies/${company.slug}?window=${w}`}
            className={`${styles.windowTab} ${w === window ? styles.windowTabActive : ""}`}
            aria-current={w === window ? "page" : undefined}
          >
            {WINDOW_LABELS[w]}
          </Link>
        ))}
      </nav>

      <section className={styles.metrics} aria-label="핵심 지표">
        <MetricCard
          label="결과 통보율"
          value={formatRate(metrics.response_rate)}
          caption="합격·불합격 등 명시적 결과를 받은 비율"
          tone="alive"
          icon="response"
        />
        <MetricCard
          label="무응답률"
          value={formatRate(metrics.ghost_rate)}
          caption="관측 기간이 지나도 결과를 받지 못한 비율"
          tone="extinct"
          icon="silence"
        />
        <MetricCard
          label="응답 소요"
          value={formatDays(metrics.median_response_days)}
          caption="결과를 받은 경우의 중앙값"
        />
      </section>

      {/* Sample size and window travel with every rate, always (docs/08 §8). */}
      <p className={styles.provenance}>
        <span className="gd-tabular">n={metrics.qualified_n}</span> ·{" "}
        {windowLabel} ·{" "}
        <span className="gd-tabular">
          검증 비율 {Math.round(metrics.verified_ratio * 100)}%
        </span>{" "}
        · <strong>{ELIGIBILITY_LABELS[metrics.eligibility]}</strong> ·{" "}
        <Link href="/methodology" className={styles.methodLink}>
          측정 기준 {metrics.methodology_version}
        </Link>
      </p>
      <p className={styles.eligibilityNote}>{ELIGIBILITY_NOTES[metrics.eligibility]}</p>

      {metrics.promised_timeline_n > 0 && (
        <section className={styles.promiseBlock} aria-label="약속 이행">
          <h2 className={styles.h2}>결과 안내 예정일 약속</h2>
          <p className={styles.promiseBody}>
            회사가 결과 안내 예정일을 밝힌 기록{" "}
            <span className="gd-tabular">{metrics.promised_timeline_n}건</span> 중,{" "}
            {metrics.broken_promise_rate === null ? (
              <>약속 이행 비율은 <strong>표본 부족</strong>으로 공개하지 않습니다.</>
            ) : (
              <>
                안내 없이 예정일을 넘긴 비율은{" "}
                <strong className="gd-tabular">
                  {formatRate(metrics.broken_promise_rate)}
                </strong>
                입니다.
              </>
            )}
          </p>
        </section>
      )}

      <section aria-label="단계별 기록">
        <h2 className={styles.h2}>
          <FootprintMark size={20} className={styles.h2Mark} />
          단계별 기록
        </h2>
        <StageBreakdown stages={metrics.stage_breakdown} />
      </section>

      {jobs.length > 0 && (
        <section aria-label="채용공고">
          <div className={styles.jobsHead}>
            <h2 className={styles.h2}>
              <FieldNotebook size={20} className={styles.h2Mark} />
              지금 열려 있는 공고
            </h2>
            <Link href={`/companies/${company.slug}/jobs`} className={styles.jobsLink}>
              전체 공고 보기
            </Link>
          </div>
          <JobCardList jobs={jobs} showCompany={false} />
        </section>
      )}

      <section aria-label="최근 관측 기록">
        <h2 className={styles.h2}>
          <TimelineBone size={20} className={styles.h2Mark} />
          최근 관측 기록
        </h2>
        <ReportCardList reports={reports} />
      </section>

      <section className={styles.correction}>
        <h2 className={styles.correctionTitle}>사실관계가 다른가요?</h2>
        <p className={styles.correctionBody}>
          회사 관계자는 기록에 대한 정정을 요청할 수 있습니다. 정정 절차는
          기록의 내용을 다루며, 작성자의 신원은 어떤 경우에도 공개되지 않습니다.
        </p>
        <CorrectionForm slug={company.slug} />
        <Link href="/company-portal/claim" className={styles.correctionLink}>
          정정 절차 자세히 보기
        </Link>
      </section>
    </article>
  );
}
