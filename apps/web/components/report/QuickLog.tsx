"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, ApiUnavailableError, apiRequest } from "@/lib/api/client";
import {
  APPLICATION_SOURCES,
  EMPLOYMENT_LABELS,
  EMPLOYMENT_TYPES,
  HIRING_STAGES,
  OUTCOME_LABELS,
  ROLE_CATEGORIES,
  ROLE_LABELS,
  SOURCE_LABELS,
  STAGE_LABELS,
  type HiringStage,
} from "@/lib/domain";
import {
  QUICK_LOG_MAX_ITEMS,
  blankRow,
  hasErrors,
  toQuickLogInput,
  validateQuickLog,
  type QuickLogDefaults,
  type QuickLogErrors,
  type QuickLogRow,
} from "@/lib/validation/quick-log";

import { CompanyPicker } from "./CompanyPicker";
import styles from "./QuickLog.module.css";

const STORAGE_KEY = "ghostdodo.quicklog.draft.v1";
const RECEIVED_OUTCOMES = ["PASSED", "REJECTED", "WITHDREW"] as const;

type ItemResult = {
  index: number;
  status: "SUBMITTED" | "DUPLICATE" | "LIMIT" | "INVALID";
  message: string | null;
};
type BatchResult = { batch_id: string; submitted: number; results: ItemResult[] };

const RESULT_LABELS: Record<ItemResult["status"], string> = {
  SUBMITTED: "기록됨",
  DUPLICATE: "이미 기록한 지원입니다",
  LIMIT: "이 회사에 남길 수 있는 기록 수를 넘었습니다",
  INVALID: "확인이 필요합니다",
};

const DEFAULTS: QuickLogDefaults = {
  role_title: "",
  role_category: "SOFTWARE_ENGINEERING",
  employment_type: "FULL_TIME",
  source: "COMPANY_SITE",
};

let nextKey = 0;
const newKey = () => `row-${Date.now()}-${nextKey++}`;

/**
 * Many companies, one submission.
 *
 * What is shared — the role, the employment type, where applications went —
 * is chosen once; each company is one short line. Every line is filed as an
 * ordinary report through the same path as the wizard, so it is checked the
 * same way, and a moderator reviews the set together.
 *
 * The draft lives in this browser until it is submitted, so being sent to
 * sign in halfway through thirty lines loses nothing.
 */
export function QuickLog() {
  const [defaults, setDefaults] = useState<QuickLogDefaults>(DEFAULTS);
  const [rows, setRows] = useState<QuickLogRow[]>(() => [blankRow(newKey())]);
  const [errors, setErrors] = useState<QuickLogErrors>({ defaults: {}, rows: {} });
  const [restored, setRestored] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [result, setResult] = useState<BatchResult | null>(null);

  // Restore after mount, not during render: the server has no localStorage,
  // and reading it in the initialiser would mismatch hydration.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as { defaults: QuickLogDefaults; rows: QuickLogRow[] };
        if (parsed.rows?.length) {
          // eslint-disable-next-line react-hooks/set-state-in-effect -- browser-only storage, read once after mount (see ReportWizard)
          setDefaults(parsed.defaults);
          setRows(parsed.rows);
        }
      }
    } catch {
      /* a corrupt or blocked store just starts fresh */
    }
    // Saving waits for this, so the blank first render never overwrites a
    // saved draft before it is read.
    setRestored(true);
  }, []);

  useEffect(() => {
    if (!restored || result) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ defaults, rows }));
    } catch {
      /* storage is a convenience, never a requirement */
    }
  }, [defaults, rows, restored, result]);

  function updateRow(key: string, patch: Partial<QuickLogRow>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  async function submit() {
    const found = validateQuickLog(defaults, rows);
    setErrors(found);
    if (hasErrors(found)) {
      setSubmitError("입력하지 않았거나 확인이 필요한 칸이 있습니다.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    setNeedsSignIn(false);
    try {
      const done = await apiRequest<BatchResult>("/reports/batch", {
        method: "POST",
        body: toQuickLogInput(defaults, rows),
      });
      setResult(done);
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        /* ignore */
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) setNeedsSignIn(true);
        else if (error.code === "RATE_LIMITED") {
          setSubmitError("오늘 제출할 수 있는 횟수를 넘었습니다. 내일 다시 시도해 주세요.");
        } else setSubmitError(error.message);
      } else if (error instanceof ApiUnavailableError) {
        setSubmitError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      } else {
        setSubmitError("기록을 저장하지 못했습니다.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className={styles.done} role="status">
        <h2 className={styles.doneTitle}>
          <span className="gd-tabular">{result.submitted}</span>건을 기록했습니다
        </h2>
        <p className={styles.doneBody}>
          검토를 거친 기록만 회사 지표에 반영됩니다. 첨부 자료가 있는 기록은 내 기록에서
          하나씩 보탤 수 있습니다.
        </p>
        <ul className={styles.resultList}>
          {result.results.map((item) => (
            <li key={item.index} className={styles.resultRow}>
              <span>{rows[item.index]?.company_name ?? `${item.index + 1}번째 줄`}</span>
              <span className={item.status === "SUBMITTED" ? styles.ok : styles.notOk}>
                {RESULT_LABELS[item.status]}
                {item.status === "INVALID" && item.message ? ` · ${item.message}` : ""}
              </span>
            </li>
          ))}
        </ul>
        <div className={styles.doneActions}>
          <Link href="/me/reports" className={styles.primaryButton}>
            내 기록 보기
          </Link>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => {
              setResult(null);
              setRows([blankRow(newKey())]);
              setErrors({ defaults: {}, rows: {} });
            }}
          >
            더 기록하기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <section className={styles.card} aria-labelledby="quicklog-shared">
        <h2 id="quicklog-shared" className={styles.h2}>
          공통 정보
        </h2>
        <p className={styles.hint}>아래 회사들에 공통으로 적용됩니다.</p>
        <label className={styles.field}>
          <span className={styles.label}>지원한 직무</span>
          <input
            className={styles.input}
            value={defaults.role_title}
            maxLength={120}
            placeholder="예: 백엔드 개발자"
            onChange={(e) => setDefaults({ ...defaults, role_title: e.target.value })}
          />
          {errors.defaults.role_title && (
            <span className={styles.error}>{errors.defaults.role_title}</span>
          )}
        </label>
        <div className={styles.grid}>
          <label className={styles.field}>
            <span className={styles.label}>직무 분야</span>
            <select
              className={styles.input}
              value={defaults.role_category}
              onChange={(e) =>
                setDefaults({
                  ...defaults,
                  role_category: e.target.value as QuickLogDefaults["role_category"],
                })
              }
            >
              {ROLE_CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {ROLE_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            <span className={styles.label}>고용 형태</span>
            <select
              className={styles.input}
              value={defaults.employment_type}
              onChange={(e) =>
                setDefaults({
                  ...defaults,
                  employment_type: e.target.value as QuickLogDefaults["employment_type"],
                })
              }
            >
              {EMPLOYMENT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {EMPLOYMENT_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            <span className={styles.label}>지원 경로</span>
            <select
              className={styles.input}
              value={defaults.source}
              onChange={(e) =>
                setDefaults({ ...defaults, source: e.target.value as QuickLogDefaults["source"] })
              }
            >
              {APPLICATION_SOURCES.map((value) => (
                <option key={value} value={value}>
                  {SOURCE_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <ol className={styles.rows}>
        {rows.map((row, index) => {
          const e = errors.rows[row.key] ?? {};
          return (
            <li key={row.key} className={styles.card}>
              <div className={styles.rowHead}>
                <span className={styles.rowNumber}>{index + 1}</span>
                {rows.length > 1 && (
                  <button
                    type="button"
                    className={styles.remove}
                    onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}
                    aria-label={`${index + 1}번째 회사 지우기`}
                  >
                    지우기
                  </button>
                )}
              </div>

              <div className={styles.field}>
                <span className={styles.label}>회사</span>
                <CompanyPicker
                  value={row.company_name}
                  onSelect={(company) =>
                    updateRow(row.key, {
                      company_id: company.id,
                      company_name: company.display_name_ko,
                    })
                  }
                />
                {e.company_id && <span className={styles.error}>{e.company_id}</span>}
              </div>

              <div className={styles.grid}>
                <label className={styles.field}>
                  <span className={styles.label}>지원일</span>
                  <input
                    type="date"
                    className={styles.input}
                    value={row.application_date}
                    max={new Date().toISOString().slice(0, 10)}
                    onChange={(ev) => updateRow(row.key, { application_date: ev.target.value })}
                  />
                  {e.application_date && (
                    <span className={styles.error}>{e.application_date}</span>
                  )}
                </label>
                <label className={styles.field}>
                  <span className={styles.label}>어디까지 갔나요</span>
                  <select
                    className={styles.input}
                    value={row.furthest_stage}
                    onChange={(ev) =>
                      updateRow(row.key, { furthest_stage: ev.target.value as HiringStage })
                    }
                  >
                    {HIRING_STAGES.map((value) => (
                      <option key={value} value={value}>
                        {STAGE_LABELS[value]}
                      </option>
                    ))}
                  </select>
                </label>
                {row.furthest_stage !== "APPLICATION" && (
                  <label className={styles.field}>
                    <span className={styles.label}>마지막으로 연락받은 날</span>
                    <input
                      type="date"
                      className={styles.input}
                      value={row.last_contact}
                      max={new Date().toISOString().slice(0, 10)}
                      onChange={(ev) => updateRow(row.key, { last_contact: ev.target.value })}
                    />
                    {e.last_contact && <span className={styles.error}>{e.last_contact}</span>}
                  </label>
                )}
              </div>

              <fieldset className={styles.field}>
                <legend className={styles.label}>결과를 받았나요</legend>
                <div className={styles.toggles}>
                  <button
                    type="button"
                    className={`${styles.toggle} ${!row.result_received ? styles.toggleActive : ""}`}
                    aria-pressed={!row.result_received}
                    onClick={() => updateRow(row.key, { result_received: false })}
                  >
                    아직 못 받음
                  </button>
                  <button
                    type="button"
                    className={`${styles.toggle} ${row.result_received ? styles.toggleActive : ""}`}
                    aria-pressed={row.result_received}
                    onClick={() => updateRow(row.key, { result_received: true })}
                  >
                    받음
                  </button>
                </div>
              </fieldset>

              {row.result_received && (
                <div className={styles.grid}>
                  <label className={styles.field}>
                    <span className={styles.label}>받은 날</span>
                    <input
                      type="date"
                      className={styles.input}
                      value={row.result_date}
                      max={new Date().toISOString().slice(0, 10)}
                      onChange={(ev) => updateRow(row.key, { result_date: ev.target.value })}
                    />
                    {e.result_date && <span className={styles.error}>{e.result_date}</span>}
                  </label>
                  <fieldset className={styles.field}>
                    <legend className={styles.label}>결과</legend>
                    <div className={styles.toggles}>
                      {RECEIVED_OUTCOMES.map((value) => (
                        <button
                          key={value}
                          type="button"
                          className={`${styles.toggle} ${
                            row.outcome === value ? styles.toggleActive : ""
                          }`}
                          aria-pressed={row.outcome === value}
                          onClick={() => updateRow(row.key, { outcome: value })}
                        >
                          {OUTCOME_LABELS[value]}
                        </button>
                      ))}
                    </div>
                    {e.outcome && <span className={styles.error}>{e.outcome}</span>}
                  </fieldset>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {rows.length < QUICK_LOG_MAX_ITEMS ? (
        <button
          type="button"
          className={styles.addRow}
          onClick={() => setRows((current) => [...current, blankRow(newKey())])}
        >
          + 회사 추가
        </button>
      ) : (
        <p className={styles.hint}>한 번에 {QUICK_LOG_MAX_ITEMS}곳까지 기록할 수 있습니다.</p>
      )}

      {needsSignIn && (
        <div className={styles.signIn} role="alert">
          <p>기록을 남기려면 먼저 로그인해 주세요. 입력한 내용은 이 브라우저에 남아 있습니다.</p>
          <Link href="/sign-in?next=%2Freport%2Fquick" className={styles.signInLink}>
            로그인하러 가기
          </Link>
        </div>
      )}
      {submitError && (
        <p className={styles.submitError} role="alert">
          {submitError}
        </p>
      )}

      <button
        type="button"
        className={styles.primaryButton}
        disabled={submitting}
        onClick={submit}
      >
        {submitting ? "기록하는 중…" : `${rows.length}곳 기록하기`}
      </button>
    </div>
  );
}
