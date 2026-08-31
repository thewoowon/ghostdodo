"use client";

import { useState } from "react";

import { ApiError, ApiUnavailableError, apiRequest } from "@/lib/api/client";

import styles from "./CorrectionForm.module.css";

const DISPUTABLE_FIELDS = [
  { value: "result_received", label: "결과 통보 여부" },
  { value: "result_received_at", label: "결과 통보일" },
  { value: "promised_result", label: "결과 안내 예정 여부" },
  { value: "promised_result_date", label: "결과 안내 예정일" },
  { value: "application_date", label: "지원일" },
  { value: "furthest_stage", label: "진행 단계" },
  { value: "role_title", label: "직무명" },
  { value: "employment_type", label: "고용 형태" },
] as const;

const MIN_SUMMARY = 10;

/**
 * The correction route every company page is required to expose (docs/08 §5).
 *
 * Deliberately open — no account, no verified claim. Requiring ownership
 * proof first would mean the route exists but does not work, which is the
 * failure the requirement is guarding against. Submissions are rate-limited
 * and reviewed before anything changes.
 */
export function CorrectionForm({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [summary, setSummary] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  function toggleField(value: string) {
    setFields((current) =>
      current.includes(value)
        ? current.filter((f) => f !== value)
        : [...current, value],
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (summary.trim().length < MIN_SUMMARY) {
      setError(`정정을 요청하시는 내용을 ${MIN_SUMMARY}자 이상 적어 주세요.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest(`/companies/${encodeURIComponent(slug)}/corrections`, {
        method: "POST",
        body: {
          contact_email: email,
          claim_summary: summary.trim(),
          disputed_fields: fields,
        },
      });
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.code === "RATE_LIMITED"
            ? "정정 요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."
            : err.message,
        );
      } else if (err instanceof ApiUnavailableError) {
        setError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      } else {
        setError("요청을 접수하지 못했습니다.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <p className={styles.done} role="status">
        정정 요청이 접수되었습니다. 검토 후 입력하신 이메일로 결과를
        안내드립니다.
      </p>
    );
  }

  if (!open) {
    return (
      <button type="button" className={styles.trigger} onClick={() => setOpen(true)}>
        사실관계 정정 요청
      </button>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <p className={styles.privacyNote}>
        이 절차는 <strong>기록의 내용</strong>을 다룹니다. 작성자를 특정하거나
        신원을 회사에 알리지 않으며, 페이지 소유권 확인 여부와 관계없이 기록을
        삭제할 권한은 부여되지 않습니다.
      </p>

      <label className={styles.field}>
        <span className={styles.label}>회신받을 이메일</span>
        <input
          type="email"
          required
          className={styles.input}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="hr@company.com"
        />
      </label>

      <fieldset className={styles.field}>
        <legend className={styles.label}>정정을 요청하는 항목 (선택)</legend>
        <div className={styles.chips}>
          {DISPUTABLE_FIELDS.map((field) => (
            <label
              key={field.value}
              className={`${styles.chip} ${
                fields.includes(field.value) ? styles.chipActive : ""
              }`}
            >
              <input
                type="checkbox"
                className={styles.chipInput}
                checked={fields.includes(field.value)}
                onChange={() => toggleField(field.value)}
              />
              {field.label}
            </label>
          ))}
        </div>
        <p className={styles.hint}>
          지원자의 최종 결과나 서술 내용은 지원자 본인의 진술이므로 정정 대상이
          아닙니다.
        </p>
      </fieldset>

      <label className={styles.field}>
        <span className={styles.label}>사실관계 설명</span>
        <textarea
          required
          rows={4}
          className={styles.textarea}
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="예: 해당 기간 지원자 전원에게 2026-07-20에 결과 메일을 발송했으며 발송 로그를 보유하고 있습니다."
          maxLength={2000}
        />
      </label>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.cancel}
          onClick={() => setOpen(false)}
          disabled={submitting}
        >
          취소
        </button>
        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "접수 중…" : "정정 요청 보내기"}
        </button>
      </div>
    </form>
  );
}
