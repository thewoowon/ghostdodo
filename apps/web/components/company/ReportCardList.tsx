import { DodoEgg, EvidenceStamp } from "@/components/brand/svg/marks";
import type { PublicReportCard } from "@/lib/api/types";
import {
  EMPLOYMENT_LABELS,
  OUTCOME_LABELS,
  ROLE_LABELS,
  STAGE_LABELS,
  VERIFICATION_LABELS,
} from "@/lib/domain";
import { formatShortDate } from "@/lib/format/metrics";

import styles from "./ReportCardList.module.css";

/**
 * Individual observations.
 *
 * These render structured events — dates, stages, promises, outcomes — and
 * never a free-form accusation or anything identifying the reporter
 * (docs/08 §1, §4).
 */
export function ReportCardList({ reports }: { reports: PublicReportCard[] }) {
  if (reports.length === 0) {
    return (
      <div className={styles.empty}>
        <DodoEgg size={30} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>아직 공개된 기록이 없습니다</p>
        <p className={styles.emptyBody}>
          검증을 마친 기록이 쌓이면 이곳에 표시됩니다.
        </p>
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {reports.map((report) => {
        const applied = formatShortDate(report.application_date);
        const received = formatShortDate(report.result_received_at);
        const promised = formatShortDate(report.promised_result_date);

        return (
          <li key={report.id} className={styles.card}>
            <div className={styles.head}>
              <span className={styles.stage}>
                {STAGE_LABELS[report.furthest_stage]}
              </span>
              <span className={styles.role}>
                {ROLE_LABELS[report.role_category]} ·{" "}
                {EMPLOYMENT_LABELS[report.employment_type]}
              </span>
              {report.verification_status === "VERIFIED" && (
                <span className={styles.verified}>
                  <EvidenceStamp size={14} />
                  {VERIFICATION_LABELS.VERIFIED}
                </span>
              )}
            </div>

            <dl className={styles.timeline}>
              <div className={styles.row}>
                <dt>지원</dt>
                <dd className="gd-tabular">{applied ?? "—"}</dd>
              </div>
              {report.promised_result && (
                <div className={styles.row}>
                  <dt>결과 안내 예정</dt>
                  <dd className="gd-tabular">{promised ?? "예정일 명시"}</dd>
                </div>
              )}
              <div className={styles.row}>
                <dt>결과 통보</dt>
                <dd className={report.result_received ? styles.received : styles.silent}>
                  {report.result_received
                    ? `${received ?? "수신"} · ${OUTCOME_LABELS[report.outcome]}`
                    : "현재까지 미수신"}
                </dd>
              </div>
            </dl>

            {report.free_context && (
              <p className={styles.context}>{report.free_context}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
