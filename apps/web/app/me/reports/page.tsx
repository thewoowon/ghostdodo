import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { DodoEgg, EvidenceStamp } from "@/components/brand/svg/marks";
import { load } from "@/lib/api/load";
import { getMyReports } from "@/lib/api/queries";
import {
  EMPLOYMENT_LABELS,
  OUTCOME_LABELS,
  ROLE_LABELS,
  STAGE_LABELS,
  VERIFICATION_LABELS,
} from "@/lib/domain";
import { formatShortDate } from "@/lib/format/metrics";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "내 기록",
  robots: { index: false, follow: false },
};

// A moderation decision must be visible on the next load, never a cached one.
export const dynamic = "force-dynamic";

export default async function MyReportsPage() {
  const cookieHeader = (await cookies()).toString();
  const result = await load(() => getMyReports(cookieHeader));

  if (!result.ok) {
    if (result.failure === "unauthenticated") {
      return (
        <div className={`gd-shell ${styles.gate}`}>
          <DodoEgg size={34} className={styles.gateMark} />
          <h1 className={styles.gateTitle}>로그인이 필요합니다</h1>
          <p className={styles.gateBody}>
            내가 남긴 기록과 검토 상태는 로그인 후 볼 수 있습니다.
          </p>
          <Link href="/sign-in?next=%2Fme%2Freports" className={styles.gateLink}>
            로그인하기
          </Link>
        </div>
      );
    }
    return (
      <div className={`gd-shell ${styles.gate}`}>
        <h1 className={styles.gateTitle}>지금은 기록을 불러올 수 없습니다</h1>
        <p className={styles.gateBody}>
          일시적인 연결 문제입니다. 잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  const reports = result.data;

  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>내 기록</h1>
        <p className={styles.lede}>
          검토를 마친 기록만 회사 지표에 반영됩니다. 작성자의 신원은 공개
          페이지에도, 회사에도 표시되지 않습니다.
        </p>
      </header>

      {reports.length === 0 ? (
        <div className={styles.empty}>
          <DodoEgg size={30} className={styles.emptyMark} />
          <p className={styles.emptyTitle}>아직 남긴 기록이 없습니다</p>
          <Link href="/report/new" className={styles.emptyLink}>
            채용 과정 기록하기
          </Link>
        </div>
      ) : (
        <ul className={styles.list}>
          {reports.map((report) => (
            <li key={report.id} className={styles.card}>
              <Link
                href={`/companies/${report.company_slug}`}
                className={styles.company}
              >
                {report.company_name}
              </Link>
              <div className={styles.head}>
                <span className={styles.status}>
                  {VERIFICATION_LABELS[report.verification_status]}
                </span>
                <span className={styles.role}>
                  {ROLE_LABELS[report.role_category]} ·{" "}
                  {EMPLOYMENT_LABELS[report.employment_type]}
                </span>
                {report.evidence_count > 0 && (
                  <span className={styles.evidence}>
                    <EvidenceStamp size={14} />
                    증빙 {report.evidence_count}건
                  </span>
                )}
              </div>

              <dl className={styles.meta}>
                <div className={styles.row}>
                  <dt>진행 단계</dt>
                  <dd>{STAGE_LABELS[report.furthest_stage]}</dd>
                </div>
                <div className={styles.row}>
                  <dt>지원일</dt>
                  <dd className="gd-tabular">
                    {formatShortDate(report.application_date) ?? "—"}
                  </dd>
                </div>
                <div className={styles.row}>
                  <dt>결과</dt>
                  <dd>
                    {report.result_received
                      ? OUTCOME_LABELS[report.outcome]
                      : "현재까지 미수신"}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
