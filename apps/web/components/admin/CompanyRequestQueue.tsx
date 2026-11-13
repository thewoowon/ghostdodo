"use client";

import { useState } from "react";

import { FieldNotebook } from "@/components/brand/svg/marks";
import {
  type CompanyRequestDecision,
  type CompanyRequestItem,
  decideCompanyRequest,
} from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { formatShortDate } from "@/lib/format/metrics";

// Same card, buttons, and inputs as the correction queue.
import styles from "./DisputeQueue.module.css";

/**
 * Requests to add a company the directory does not have.
 *
 * A variant spelling of a company that already exists should be merged, not
 * created twice — that would split its reports and keep both halves under
 * the sample bar — so the closest existing companies are listed with each
 * request. An approved company is real, and the launch gate holds it back
 * like any import.
 *
 * The submitted website is shown as text, never as a link: it is a
 * stranger's input, and a stored URL reaching an `href` needs its scheme
 * checked first.
 */
export function CompanyRequestQueue({ initial }: { initial: CompanyRequestItem[] }) {
  const [items, setItems] = useState(initial);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mergeTarget, setMergeTarget] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});

  async function decide(item: CompanyRequestItem, decision: CompanyRequestDecision) {
    const target = mergeTarget[item.id];
    if (decision === "MERGE" && !target) {
      setError("연결할 기존 회사를 먼저 고르세요.");
      return;
    }
    setBusy(item.id);
    setError(null);
    try {
      await decideCompanyRequest(item.id, {
        decision,
        ...(decision === "MERGE" && target ? { company_slug: target } : {}),
        ...(notes[item.id] ? { note: notes[item.id] } : {}),
      });
      setItems((current) => current.filter((row) => row.id !== item.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "결정을 저장하지 못했습니다.");
    } finally {
      setBusy(null);
    }
  }

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <FieldNotebook size={30} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>대기 중인 등록 요청이 없습니다</p>
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
          const target = mergeTarget[item.id];
          return (
            <li key={item.id} className={styles.card}>
              <header className={styles.head}>
                <span className={styles.received}>
                  접수 {formatShortDate(item.created_at) ?? "—"}
                </span>
              </header>

              <p className={styles.claim}>{item.submitted_name}</p>
              {item.website && <p className={styles.contact}>웹사이트: {item.website}</p>}
              {item.note && <p className={styles.note}>{item.note}</p>}

              {item.possible_matches.length > 0 && (
                <div role="group" aria-label="비슷한 기존 회사">
                  <p className={styles.fields}>비슷한 기존 회사</p>
                  <div className={styles.outcomes}>
                    {item.possible_matches.map((company) => (
                      <button
                        key={company.slug}
                        type="button"
                        className={`${styles.outcomeButton} ${
                          target === company.slug ? styles.outcomeActive : ""
                        }`}
                        aria-pressed={target === company.slug}
                        onClick={() =>
                          setMergeTarget((current) => ({
                            ...current,
                            [item.id]: company.slug,
                          }))
                        }
                      >
                        {company.display_name_ko}
                        {company.industry ? ` · ${company.industry}` : ""}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <label className={styles.noteField}>
                <span>메모 (감사 로그에 남습니다)</span>
                <input
                  className={styles.input}
                  value={notes[item.id] ?? ""}
                  onChange={(event) =>
                    setNotes((current) => ({ ...current, [item.id]: event.target.value }))
                  }
                  maxLength={500}
                />
              </label>

              <div className={styles.outcomes} role="group" aria-label="처리 결정">
                <button
                  type="button"
                  className={styles.submit}
                  disabled={busy === item.id}
                  onClick={() => decide(item, "APPROVE")}
                >
                  새 회사로 추가
                </button>
                <button
                  type="button"
                  className={styles.outcomeButton}
                  disabled={busy === item.id || !target}
                  onClick={() => decide(item, "MERGE")}
                >
                  선택한 회사로 연결
                </button>
                <button
                  type="button"
                  className={styles.outcomeButton}
                  disabled={busy === item.id}
                  onClick={() => decide(item, "REJECT")}
                >
                  반려
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}
