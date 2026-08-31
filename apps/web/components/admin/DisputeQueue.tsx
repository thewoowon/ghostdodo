"use client";

import { useState } from "react";

import { FieldNotebook } from "@/components/brand/svg/marks";
import {
  CORRECTION_OUTCOMES,
  OUTCOME_LABELS,
  type CorrectionOutcome,
  type DisputeItem,
  decideDispute,
} from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { formatShortDate } from "@/lib/format/metrics";

import styles from "./DisputeQueue.module.css";

const FIELD_LABELS: Record<string, string> = {
  application_date: "지원일",
  furthest_stage: "진행 단계",
  promised_result: "결과 안내 예정 여부",
  promised_result_date: "결과 안내 예정일",
  result_received: "결과 통보 여부",
  result_received_at: "결과 통보일",
  role_title: "직무명",
  employment_type: "고용 형태",
};

/**
 * Company correction requests awaiting review.
 *
 * A CORRECTED outcome needs the replacement values, so the form only reveals
 * the field inputs for that outcome — the API rejects corrections attached to
 * any other decision.
 */
export function DisputeQueue({ initial }: { initial: DisputeItem[] }) {
  const [items, setItems] = useState(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, CorrectionOutcome>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [corrections, setCorrections] = useState<
    Record<string, Record<string, string>>
  >({});

  async function resolve(item: DisputeItem) {
    const outcome = outcomes[item.id];
    if (!outcome) {
      setError("결정을 선택해 주세요.");
      return;
    }
    setBusy(item.id);
    setError(null);
    try {
      const fields = corrections[item.id] ?? {};
      await decideDispute(item.id, {
        outcome,
        ...(notes[item.id] ? { decision_note: notes[item.id] } : {}),
        ...(outcome === "CORRECTED" && Object.keys(fields).length > 0
          ? { field_corrections: fields }
          : {}),
      });
      setItems((current) => current.filter((row) => row.id !== item.id));
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
        <FieldNotebook size={30} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>대기 중인 정정 요청이 없습니다</p>
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
          const outcome = outcomes[item.id];
          return (
            <li key={item.id} className={styles.card}>
              <header className={styles.head}>
                <span className={styles.received}>
                  접수 {formatShortDate(item.created_at) ?? "—"}
                </span>
                {item.experience_id ? (
                  <span className={styles.scope}>개별 기록 대상</span>
                ) : (
                  <span className={styles.scope}>회사 페이지 전반</span>
                )}
              </header>

              <p className={styles.claim}>{item.claim_summary}</p>

              {item.disputed_fields.length > 0 && (
                <p className={styles.fields}>
                  정정 요청 항목:{" "}
                  {item.disputed_fields
                    .map((f) => FIELD_LABELS[f] ?? f)
                    .join(", ")}
                </p>
              )}

              {item.supporting_note && (
                <p className={styles.note}>{item.supporting_note}</p>
              )}

              <p className={styles.contact}>연락처: {item.contact_email ?? "—"}</p>

              <div className={styles.outcomes} role="group" aria-label="처리 결정">
                {CORRECTION_OUTCOMES.map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`${styles.outcomeButton} ${
                      outcome === value ? styles.outcomeActive : ""
                    }`}
                    aria-pressed={outcome === value}
                    onClick={() =>
                      setOutcomes((current) => ({ ...current, [item.id]: value }))
                    }
                  >
                    {OUTCOME_LABELS[value]}
                  </button>
                ))}
              </div>

              {outcome === "CORRECTED" && item.disputed_fields.length > 0 && (
                <div className={styles.corrections}>
                  <p className={styles.correctionsTitle}>수정할 값</p>
                  {item.disputed_fields.map((field) => (
                    <label key={field} className={styles.correctionField}>
                      <span>{FIELD_LABELS[field] ?? field}</span>
                      <input
                        className={styles.input}
                        value={corrections[item.id]?.[field] ?? ""}
                        placeholder={
                          field.endsWith("_at") || field.endsWith("_date")
                            ? "YYYY-MM-DD"
                            : "true / false 또는 값"
                        }
                        onChange={(event) =>
                          setCorrections((current) => ({
                            ...current,
                            [item.id]: {
                              ...(current[item.id] ?? {}),
                              [field]: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
              )}

              <label className={styles.noteField}>
                <span>처리 사유 (내부 기록)</span>
                <textarea
                  className={styles.textarea}
                  rows={2}
                  value={notes[item.id] ?? ""}
                  onChange={(event) =>
                    setNotes((current) => ({
                      ...current,
                      [item.id]: event.target.value,
                    }))
                  }
                />
              </label>

              <button
                type="button"
                className={styles.submit}
                disabled={busy === item.id || !outcome}
                onClick={() => resolve(item)}
              >
                {busy === item.id ? "처리 중…" : "결정 적용"}
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}
