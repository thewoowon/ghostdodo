import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DodoEgg, FieldNotebook, ResponseSignal } from "@/components/brand/svg/marks";
import { VerdictBadge } from "@/components/company/VerdictBadge";
import { ApplyButton } from "@/components/jobs/ApplyButton";
import { load } from "@/lib/api/load";
import { getCompanyMetrics, getJob } from "@/lib/api/queries";
import { UnpublishedNotice } from "@/components/company/UnpublishedNotice";
import { WINDOW_LABELS } from "@/lib/domain";
import { jobClosing, jobFacets, sourceName } from "@/lib/format/jobs";
import {
  ELIGIBILITY_LABELS,
  ELIGIBILITY_NOTES,
  formatDays,
  formatRate,
  responseVerdict,
} from "@/lib/format/metrics";
import { decodeRouteParam } from "@/lib/route-params";

import styles from "./page.module.css";

type Props = {
  params: Promise<{ jobId: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const jobId = decodeRouteParam((await params).jobId);
  try {
    const job = await getJob(jobId);
    return {
      title: `${job.company.display_name_ko} ${job.title} 채용`,
      description: `${job.company.display_name_ko}의 ${job.title} 공고와 이 회사의 채용 응답 기록을 함께 확인하세요.`,
      alternates: { canonical: `/jobs/${job.id}` },
    };
  } catch {
    return { title: "공고를 찾을 수 없습니다" };
  }
}

export default async function JobPage({ params }: Props) {
  const jobId = decodeRouteParam((await params).jobId);

  const jobResult = await load(() => getJob(jobId));
  if (!jobResult.ok) {
    if (jobResult.failure === "not-found") notFound();
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

  const job = jobResult.data;

  // Fetched separately and allowed to fail on its own. The response record is
  // the reason this page exists, but a metrics outage must never be what
  // stops someone from applying.
  // A company the launch gate holds back has no record to show, so it is
  // not even asked for.
  const metricsResult = job.company.published
    ? await load(() => getCompanyMetrics(job.company.slug))
    : null;
  const metrics = metricsResult?.ok ? metricsResult.data : null;
  const verdict = metrics
    ? responseVerdict(metrics.response_rate, metrics.eligibility)
    : null;

  const closing = jobClosing(job);
  const facets = jobFacets(job);

  return (
    <article className={`gd-shell ${styles.page}`}>
      <nav className={styles.breadcrumb} aria-label="위치">
        <Link href="/jobs" className={styles.breadcrumbLink}>
          채용공고
        </Link>
        <span aria-hidden>/</span>
        <Link
          href={`/companies/${job.company.slug}`}
          className={styles.breadcrumbLink}
        >
          {job.company.display_name_ko}
        </Link>
      </nav>

      <header className={styles.header}>
        <div className={styles.headMeta}>
          <span className={styles.source}>
            <FieldNotebook size={14} />
            {sourceName(job)}
          </span>
          <span className={`${styles.closing} ${styles[closing.kind]}`}>
            {closing.label}
          </span>
          {job.company.is_demo && (
            <span className={styles.demoTag}>샘플 데이터</span>
          )}
        </div>

        <h1 className={styles.title}>{job.title}</h1>
        <p className={styles.company}>
          <Link
            href={`/companies/${job.company.slug}`}
            className={styles.companyLink}
          >
            {job.company.display_name_ko}
          </Link>
          {job.company.industry ? ` · ${job.company.industry}` : ""}
        </p>

        {facets.length > 0 && (
          <ul className={styles.facets}>
            {facets.map((facet) => (
              <li key={facet} className={styles.facet}>
                {facet}
              </li>
            ))}
          </ul>
        )}
      </header>

      {job.company.is_demo && (
        <p className={styles.demoNotice}>
          이 공고는 개발용 가상 공고입니다. 실제 채용 공고가 아닙니다.
        </p>
      )}

      {/* The product's whole premise, in the one place it matters most:
          the record is shown before the apply link, not after it. */}
      <section className={styles.record} aria-label="이 회사의 응답 기록">
        <div className={styles.recordHead}>
          <h2 className={styles.h2}>
            <ResponseSignal size={20} className={styles.h2Mark} />
            지원하기 전에
          </h2>
          {verdict && <VerdictBadge verdict={verdict} />}
        </div>

        {!job.company.published ? (
          <UnpublishedNotice compact />
        ) : metrics === null ? (
          <p className={styles.recordBody}>
            지금은 이 회사의 응답 기록을 불러오지 못했습니다.{" "}
            <Link href={`/companies/${job.company.slug}`} className={styles.recordLink}>
              회사 페이지에서 확인
            </Link>
          </p>
        ) : (
          <>
            <dl className={styles.recordStats}>
              <div className={styles.stat}>
                <dt>결과 통보율</dt>
                <dd className="gd-tabular">
                  {formatRate(metrics.response_rate) ?? "표본 부족"}
                </dd>
              </div>
              <div className={styles.stat}>
                <dt>무응답률</dt>
                <dd className="gd-tabular">
                  {formatRate(metrics.ghost_rate) ?? "표본 부족"}
                </dd>
              </div>
              <div className={styles.stat}>
                <dt>응답 소요</dt>
                <dd className="gd-tabular">
                  {formatDays(metrics.median_response_days) ?? "표본 부족"}
                </dd>
              </div>
            </dl>

            {/* Sample size and window travel with every rate, always. */}
            <p className={styles.provenance}>
              <span className="gd-tabular">n={metrics.qualified_n}</span> ·{" "}
              {WINDOW_LABELS[metrics.window]} ·{" "}
              <strong>{ELIGIBILITY_LABELS[metrics.eligibility]}</strong> ·{" "}
              <Link href="/methodology" className={styles.recordLink}>
                측정 기준 {metrics.methodology_version}
              </Link>
            </p>
            <p className={styles.eligibilityNote}>
              {ELIGIBILITY_NOTES[metrics.eligibility]}
            </p>
            <Link
              href={`/companies/${job.company.slug}`}
              className={styles.recordLink}
            >
              {job.company.display_name_ko} 기록 전체 보기
            </Link>
          </>
        )}
      </section>

      <section className={styles.apply} aria-label="지원">
        <ApplyButton
          jobId={job.id}
          applyUrl={job.apply_url}
          isOpen={job.is_open}
        />
        <p className={styles.applyNote}>
          지원서는 {sourceName(job)}에서 접수됩니다. GhostDodo는 지원서를
          대신 받거나 회사에 전달하지 않습니다.
        </p>
        {!job.is_open && (
          <p className={styles.applyNote}>
            이 공고는 마감된 것으로 확인됐습니다. 회사 페이지에서 다른 공고를
            확인해 주세요.
          </p>
        )}
      </section>

      <section className={styles.contribute}>
        <h2 className={styles.contributeTitle}>이 회사에 지원한 적 있으신가요?</h2>
        <p className={styles.contributeBody}>
          결과를 받았든 받지 못했든, 기록이 쌓여야 다음 지원자가 판단할 수
          있습니다.
        </p>
        <Link href="/report/new" className={styles.contributeLink}>
          채용 과정 기록하기
        </Link>
      </section>
    </article>
  );
}
