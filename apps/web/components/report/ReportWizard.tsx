"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, ApiUnavailableError, apiRequest } from "@/lib/api/client";
import type { OwnReport } from "@/lib/api/types";
import {
  APPLICATION_SOURCES,
  CHANNELS,
  CHANNEL_LABELS,
  EMPLOYMENT_LABELS,
  EMPLOYMENT_TYPES,
  HIRING_STAGES,
  OUTCOMES,
  OUTCOME_LABELS,
  ROLE_CATEGORIES,
  ROLE_LABELS,
  SOURCE_LABELS,
  STAGE_LABELS,
} from "@/lib/domain";
import {
  EMPTY_DRAFT,
  FREE_CONTEXT_MAX,
  type WizardDraft,
  companyStepSchema,
  contextStepSchema,
  detectPossiblePii,
  outcomeStepSchema,
  timelineStepSchema,
  toReportInput,
} from "@/lib/validation/report";

import { CompanyPicker } from "./CompanyPicker";
import styles from "./ReportWizard.module.css";

const DRAFT_STORAGE_KEY = "ghostdodo.report.draft.v1";

const STEPS = [
  { id: "company", label: "회사" },
  { id: "context", label: "지원 정보" },
  { id: "stage", label: "진행 단계" },
  { id: "timeline", label: "연락 시점" },
  { id: "outcome", label: "결과" },
  { id: "review", label: "확인" },
] as const;

type StepId = (typeof STEPS)[number]["id"];
type Errors = Partial<Record<string, string>>;

/**
 * The report submission flow.
 *
 * Deliberately a calm wizard rather than one long angry textarea (docs/03 §5):
 * structured fields first, short optional prose last, and an explicit preview
 * of what becomes public before anything is submitted.
 */
export function ReportWizard() {
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState<WizardDraft>(EMPTY_DRAFT);
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<OwnReport | null>(null);
  const [restored, setRestored] = useState(false);

  const step = STEPS[stepIndex]!;
  const isDirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(EMPTY_DRAFT),
    [draft],
  );

  // Restore an interrupted draft. The flow is long enough that losing it to a
  // stray refresh would cost a real contribution.
  //
  // This must be a post-mount effect rather than a lazy `useState` initializer:
  // localStorage does not exist during server rendering, so seeding state from
  // it at construction time would make the server and client render different
  // trees and trip a hydration mismatch. Reading after mount is the correct
  // shape for browser-only storage, and it runs exactly once.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!saved) return;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- see above
      setDraft({ ...EMPTY_DRAFT, ...(JSON.parse(saved) as Partial<WizardDraft>) });
      setRestored(true);
    } catch {
      // A blocked or corrupt store is not worth failing the page over.
    }
  }, []);

  useEffect(() => {
    if (!isDirty || submitted) return;
    try {
      window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
    } catch {
      /* ignore */
    }
  }, [draft, isDirty, submitted]);

  // Warn before leaving mid-flow (docs/04 §7).
  useEffect(() => {
    if (!isDirty || submitted) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty, submitted]);

  const update = useCallback(<K extends keyof WizardDraft>(key: K, value: WizardDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  }, []);

  function validateStep(id: StepId): boolean {
    const schema = {
      company: companyStepSchema,
      context: contextStepSchema,
      stage: null,
      timeline: timelineStepSchema,
      outcome: outcomeStepSchema,
      review: null,
    }[id];

    if (!schema) return true;

    const result = schema.safeParse(draft);
    if (result.success) {
      setErrors({});
      return true;
    }
    const next: Errors = {};
    for (const issue of result.error.issues) {
      const key = issue.path[0];
      if (typeof key === "string" && !next[key]) next[key] = issue.message;
    }
    setErrors(next);
    return false;
  }

  function goNext() {
    if (!validateStep(step.id)) return;
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  }

  function goBack() {
    setErrors({});
    setStepIndex((i) => Math.max(i - 1, 0));
  }

  async function submit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      // Create then submit: the draft exists server-side before it enters the
      // verification pipeline, so a failure at submit does not lose the data.
      const created = await apiRequest<OwnReport>("/reports", {
        method: "POST",
        body: toReportInput(draft),
        idempotencyKey: crypto.randomUUID(),
      });
      const final = await apiRequest<OwnReport>(`/reports/${created.id}/submit`, {
        method: "POST",
      });
      setSubmitted(final);
      try {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      } catch {
        /* ignore */
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(
          error.code === "UNAUTHORIZED"
            ? "기록을 남기려면 먼저 로그인해 주세요."
            : error.message,
        );
      } else if (error instanceof ApiUnavailableError) {
        setSubmitError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      } else {
        setSubmitError("기록을 저장하지 못했습니다.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const piiWarnings = detectPossiblePii(draft.free_context);

  if (submitted) {
    return (
      <div className={styles.done} role="status">
        <h2 className={styles.doneTitle}>기록이 접수되었습니다</h2>
        <p className={styles.doneBody}>
          제출한 기록은 검토를 거친 뒤 회사 지표에 반영됩니다. 검토 결과는
          내 기록 목록에서 확인할 수 있습니다.
        </p>
        <p className={styles.doneMeta}>
          현재 상태: <strong>{submitted.verification_status}</strong>
        </p>
      </div>
    );
  }

  return (
    <div className={styles.wizard}>
      <ol className={styles.steps} aria-label="작성 단계">
        {STEPS.map((s, index) => (
          <li
            key={s.id}
            className={`${styles.stepChip} ${
              index === stepIndex
                ? styles.stepCurrent
                : index < stepIndex
                  ? styles.stepDone
                  : ""
            }`}
            aria-current={index === stepIndex ? "step" : undefined}
          >
            <span className={styles.stepIndex}>{index + 1}</span>
            {s.label}
          </li>
        ))}
      </ol>

      {restored && stepIndex === 0 && (
        <p className={styles.restored} role="status">
          작성 중이던 내용을 불러왔습니다.
        </p>
      )}

      <div className={styles.panel}>
        {step.id === "company" && (
          <Field label="어느 회사에 지원하셨나요?" error={errors.company_id}>
            <CompanyPicker
              value={draft.company_name}
              onSelect={(company) => {
                update("company_id", company.id);
                update("company_name", company.display_name_ko);
              }}
            />
          </Field>
        )}

        {step.id === "context" && (
          <>
            <Field label="지원한 직무" error={errors.role_title}>
              <input
                className={styles.input}
                value={draft.role_title}
                onChange={(e) => update("role_title", e.target.value)}
                placeholder="예: 프론트엔드 개발자"
                maxLength={120}
              />
            </Field>
            <Field label="직군">
              <select
                className={styles.input}
                value={draft.role_category}
                onChange={(e) =>
                  update("role_category", e.target.value as WizardDraft["role_category"])
                }
              >
                {ROLE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {ROLE_LABELS[c]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="고용 형태">
              <select
                className={styles.input}
                value={draft.employment_type}
                onChange={(e) =>
                  update("employment_type", e.target.value as WizardDraft["employment_type"])
                }
              >
                {EMPLOYMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {EMPLOYMENT_LABELS[t]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="지원 경로">
              <select
                className={styles.input}
                value={draft.source}
                onChange={(e) => update("source", e.target.value as WizardDraft["source"])}
              >
                {APPLICATION_SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {SOURCE_LABELS[s]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="지원한 날짜" error={errors.application_date}>
              <input
                type="date"
                className={styles.input}
                value={draft.application_date}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => update("application_date", e.target.value)}
              />
            </Field>
          </>
        )}

        {step.id === "stage" && (
          <Field label="어느 단계까지 진행하셨나요?" group>
            <div className={styles.radioGrid}>
              {HIRING_STAGES.map((s) => (
                <label
                  key={s}
                  className={`${styles.radio} ${
                    draft.furthest_stage === s ? styles.radioActive : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="furthest_stage"
                    value={s}
                    checked={draft.furthest_stage === s}
                    onChange={() => update("furthest_stage", s)}
                    className={styles.radioInput}
                  />
                  {STAGE_LABELS[s]}
                </label>
              ))}
            </div>
          </Field>
        )}

        {step.id === "timeline" && (
          <>
            <Field
              label="회사와 마지막으로 연락한 날"
              hint="회사가 마지막으로 연락해 온 시점입니다. 무응답 기간은 이 날짜부터 계산합니다."
            >
              <input
                type="date"
                className={styles.input}
                value={draft.last_company_interaction_at}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => update("last_company_interaction_at", e.target.value)}
              />
            </Field>

            <Field label="회사가 결과 안내 예정일을 알려줬나요?" group>
              <Toggle
                value={draft.promised_result}
                onChange={(v) => update("promised_result", v)}
              />
            </Field>

            {draft.promised_result && (
              <Field label="안내받은 예정일" error={errors.promised_result_date}>
                <input
                  type="date"
                  className={styles.input}
                  value={draft.promised_result_date}
                  onChange={(e) => update("promised_result_date", e.target.value)}
                />
              </Field>
            )}

            <Field label="결과를 통보받으셨나요?" group>
              <Toggle
                value={draft.result_received}
                onChange={(v) => update("result_received", v)}
              />
            </Field>

            {draft.result_received && (
              <>
                <Field label="결과를 받은 날짜" error={errors.result_received_at}>
                  <input
                    type="date"
                    className={styles.input}
                    value={draft.result_received_at}
                    max={new Date().toISOString().slice(0, 10)}
                    onChange={(e) => update("result_received_at", e.target.value)}
                  />
                </Field>
                <Field label="전달 경로">
                  <select
                    className={styles.input}
                    value={draft.result_channel}
                    onChange={(e) =>
                      update("result_channel", e.target.value as WizardDraft["result_channel"])
                    }
                  >
                    <option value="">선택 안 함</option>
                    {CHANNELS.map((c) => (
                      <option key={c} value={c}>
                        {CHANNEL_LABELS[c]}
                      </option>
                    ))}
                  </select>
                </Field>
              </>
            )}
          </>
        )}

        {step.id === "outcome" && (
          <>
            <Field label="최종 결과" group>
              <div className={styles.radioGrid}>
                {OUTCOMES.map((o) => (
                  <label
                    key={o}
                    className={`${styles.radio} ${
                      draft.outcome === o ? styles.radioActive : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="outcome"
                      value={o}
                      checked={draft.outcome === o}
                      onChange={() => update("outcome", o)}
                      className={styles.radioInput}
                    />
                    {OUTCOME_LABELS[o]}
                  </label>
                ))}
              </div>
            </Field>

            <Field
              label="추가 설명 (선택)"
              hint="사실만 짧게 적어 주세요. 개인의 이름이나 연락처, 인격에 대한 표현은 기록할 수 없습니다."
              error={errors.free_context}
            >
              <textarea
                className={styles.textarea}
                value={draft.free_context}
                maxLength={FREE_CONTEXT_MAX}
                rows={4}
                onChange={(e) => update("free_context", e.target.value)}
                placeholder="예: 결과 안내 예정일 이후 별도 안내를 받지 못함"
              />
              <p className={`${styles.counter} gd-tabular`}>
                {draft.free_context.length} / {FREE_CONTEXT_MAX}
              </p>
            </Field>

            {piiWarnings.length > 0 && (
              <div className={styles.piiWarning} role="alert">
                <p className={styles.piiTitle}>공개 전에 확인해 주세요</p>
                <ul className={styles.piiList}>
                  {piiWarnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {step.id === "review" && (
          <div className={styles.review}>
            <h2 className={styles.reviewTitle}>공개되는 내용</h2>
            <dl className={styles.reviewList}>
              <Row label="회사" value={draft.company_name} />
              <Row label="직군" value={ROLE_LABELS[draft.role_category]} />
              <Row label="고용 형태" value={EMPLOYMENT_LABELS[draft.employment_type]} />
              <Row label="진행 단계" value={STAGE_LABELS[draft.furthest_stage]} />
              <Row label="지원일" value={draft.application_date} />
              <Row
                label="결과 안내 예정일"
                value={draft.promised_result ? draft.promised_result_date : "없음"}
              />
              <Row
                label="결과 통보"
                value={
                  draft.result_received
                    ? `${draft.result_received_at} · ${OUTCOME_LABELS[draft.outcome]}`
                    : "미수신"
                }
              />
              {draft.free_context && <Row label="설명" value={draft.free_context} />}
            </dl>

            <h2 className={styles.reviewTitle}>공개되지 않는 내용</h2>
            <ul className={styles.privateList}>
              <li>작성자 계정 정보 — 회사에도, 다른 이용자에게도 공개되지 않습니다.</li>
              <li>지원한 직무명 원문 — 직군으로만 집계됩니다.</li>
              <li>첨부한 자료 — 검증 목적으로만 열람됩니다.</li>
            </ul>

            {submitError && (
              <p className={styles.submitError} role="alert">
                {submitError}
              </p>
            )}
          </div>
        )}
      </div>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={goBack}
          disabled={stepIndex === 0 || submitting}
        >
          이전
        </button>
        {step.id === "review" ? (
          <button
            type="button"
            className={styles.primaryButton}
            onClick={submit}
            disabled={submitting}
          >
            {submitting ? "제출하는 중…" : "기록 제출하기"}
          </button>
        ) : (
          <button type="button" className={styles.primaryButton} onClick={goNext}>
            다음
          </button>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  error,
  group = false,
  children,
}: {
  label: string;
  hint?: string;
  error?: string | undefined;
  /**
   * True when the field holds several controls (radios, a yes/no toggle).
   * A `<label>` may only name ONE control — wrapping a group in one makes
   * clicking the text activate an arbitrary button and gives screen readers
   * a nonsensical name — so groups get a fieldset/legend instead.
   */
  group?: boolean;
  children: React.ReactNode;
}) {
  const inner = (
    <>
      {hint && <span className={styles.hint}>{hint}</span>}
      {children}
      {error && (
        <span className={styles.error} role="alert">
          {error}
        </span>
      )}
    </>
  );

  if (group) {
    return (
      <fieldset className={styles.field}>
        <legend className={styles.label}>{label}</legend>
        {inner}
      </fieldset>
    );
  }

  return (
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {inner}
    </label>
  );
}

function Toggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className={styles.toggleGroup} role="group">
      <button
        type="button"
        className={`${styles.toggle} ${value ? styles.toggleActive : ""}`}
        onClick={() => onChange(true)}
        aria-pressed={value}
      >
        예
      </button>
      <button
        type="button"
        className={`${styles.toggle} ${!value ? styles.toggleActive : ""}`}
        onClick={() => onChange(false)}
        aria-pressed={!value}
      >
        아니오
      </button>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.reviewRow}>
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}
