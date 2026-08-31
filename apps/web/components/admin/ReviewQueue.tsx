"use client";

import { useState } from "react";

import { EvidenceStamp, SilenceSignal } from "@/components/brand/svg/marks";
import {
  AUTO_CHECK_LABELS,
  DECISION_LABELS,
  REVIEW_DECISIONS,
  type QueueItem,
  type ReviewDecision,
  decideReport,
} from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import {
  EMPLOYMENT_LABELS,
  OUTCOME_LABELS,
  ROLE_LABELS,
  STAGE_LABELS,
  VERIFICATION_LABELS,
  type VerificationStatus,
} from "@/lib/domain";
import { formatShortDate } from "@/lib/format/metrics";

import { EvidenceViewer } from "./EvidenceViewer";
import styles from "./ReviewQueue.module.css";

/**
 * The moderation queue.
 *
 * A decision here is irreversible from the moderator's side — it writes an
 * audit row, moves reputation, and recomputes the company's public numbers —
 * so destructive decisions require an explicit confirmation step rather than
 * a single click.
 */
export function ReviewQueue({ initial }: { initial: QueueItem[] }) {
  const [items, setItems] = useState(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<{
    id: string;
    decision: ReviewDecision;
  } | null>(null);

  const DESTRUCTIVE: ReviewDecision[] = ["REJECT", "REMOVE", "REQUEST_REDACTION"];

  async function apply(id: string, decision: ReviewDecision, note?: string) {
    setBusy(id);
    setError(null);
    try {
      await decideReport(id, { decision, ...(note ? { note } : {}) });
      // Drop it from the queue rather than refetching: the decision has
      // already moved it out of the reviewable set.
      setItems((current) => current.filter((item) => item.id !== id));
      setConfirming(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "결정을 저장하지 못했습니다.",
      );
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <EvidenceStamp size={30} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>검토할 기록이 없습니다</p>
        <p className={styles.emptyBody}>대기 중인 제출물이 모두 처리되었습니다.</p>
      </div>
    );
  }

  return (
    <>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <ul className={styles.list}>
        {items.map((item) => {
          const flags = Object.entries(item.auto_check_flags).filter(([, v]) => v);
          const isConfirming = confirming?.id === item.id;

          return (
            <li key={item.id} className={styles.card}>
              <header className={styles.head}>
                <span className={styles.stage}>
                  {STAGE_LABELS[item.furthest_stage]}
                </span>
                <span className={styles.meta}>
                  {ROLE_LABELS[item.role_category]} ·{" "}
                  {EMPLOYMENT_LABELS[item.employment_type]}
                </span>
                <span className={styles.status}>
                  {VERIFICATION_LABELS[item.verification_status as VerificationStatus]}
                </span>
              </header>

              {flags.length > 0 && (
                <div className={styles.flags}>
                  <SilenceSignal size={16} className={styles.flagMark} />
                  <span className={styles.flagList}>
                    {flags
                      .map(([key]) => AUTO_CHECK_LABELS[key] ?? key)
                      .join(" · ")}
                  </span>
                </div>
              )}

              <dl className={styles.facts}>
                <div>
                  <dt>지원일</dt>
                  <dd className="gd-tabular">
                    {formatShortDate(item.application_date) ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt>결과 안내 예정</dt>
                  <dd className="gd-tabular">
                    {item.promised_result
                      ? (formatShortDate(item.promised_result_date) ?? "명시됨")
                      : "없음"}
                  </dd>
                </div>
                <div>
                  <dt>결과 통보</dt>
                  <dd>
                    {item.result_received
                      ? `${formatShortDate(item.result_received_at) ?? "수신"} · ${OUTCOME_LABELS[item.outcome]}`
                      : "미수신"}
                  </dd>
                </div>
                <div>
                  <dt>첨부 자료</dt>
                  <dd className="gd-tabular">{item.evidence_count}건</dd>
                </div>
              </dl>

              {item.free_context && (
                <p className={styles.context}>{item.free_context}</p>
              )}

              {item.evidence_count > 0 && <EvidenceViewer reportId={item.id} />}

              {isConfirming ? (
                <div className={styles.confirm} role="alertdialog">
                  <p className={styles.confirmText}>
                    <strong>{DECISION_LABELS[confirming.decision]}</strong> 결정을
                    적용합니다. 이 작업은 감사 로그에 기록되고 회사 지표가 즉시
                    다시 계산됩니다.
                  </p>
                  <div className={styles.confirmActions}>
                    <button
                      type="button"
                      className={styles.cancelButton}
                      onClick={() => setConfirming(null)}
                    >
                      취소
                    </button>
                    <button
                      type="button"
                      className={styles.dangerButton}
                      disabled={busy === item.id}
                      onClick={() => apply(item.id, confirming.decision)}
                    >
                      {busy === item.id ? "적용 중…" : "확인하고 적용"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className={styles.actions}>
                  {REVIEW_DECISIONS.map((decision) => {
                    const destructive = DESTRUCTIVE.includes(decision);
                    return (
                      <button
                        key={decision}
                        type="button"
                        className={
                          destructive ? styles.dangerAction : styles.action
                        }
                        disabled={busy === item.id}
                        onClick={() =>
                          destructive
                            ? setConfirming({ id: item.id, decision })
                            : apply(item.id, decision)
                        }
                      >
                        {DECISION_LABELS[decision]}
                      </button>
                    );
                  })}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
