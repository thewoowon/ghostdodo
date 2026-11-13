"use client";

import Link from "next/link";
import { useState } from "react";

import { ApiError, ApiUnavailableError, apiRequest } from "@/lib/api/client";

import styles from "./CompanyRequestForm.module.css";

type Accepted = {
  id: string | null;
  status: "PENDING" | "EXISTS";
  message: string;
  existing_slug: string | null;
};

/**
 * Ask for a company the directory does not have.
 *
 * The import covers 법인 with 20+ members, so a small or new company — often
 * exactly where someone applied — arrives this way. A moderator reviews
 * every request before it becomes a company; the API rate-limits it and
 * collapses repeats of the same name into one queue entry. When the name
 * already belongs to a company the search missed, the answer links to it
 * instead of queueing anything.
 */
export function CompanyRequestForm({ initialName = "" }: { initialName?: string }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(initialName);
  const [website, setWebsite] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Accepted | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      setError("회사 이름을 적어 주세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      setResult(
        await apiRequest<Accepted>("/companies/request", {
          method: "POST",
          body: {
            name: name.trim(),
            website: website.trim() || null,
            note: note.trim() || null,
          },
        }),
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.code === "RATE_LIMITED"
            ? "등록 요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."
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

  if (result?.status === "EXISTS" && result.existing_slug) {
    return (
      <p className={styles.done} role="status">
        이미 도감에 있는 회사입니다.{" "}
        <Link href={`/companies/${result.existing_slug}`} className={styles.link}>
          회사 페이지로 가기
        </Link>
      </p>
    );
  }

  if (result) {
    return (
      <p className={styles.done} role="status">
        등록 요청이 접수되었습니다. 검토 후 도감에 추가되면 검색에서 찾을 수
        있습니다.
      </p>
    );
  }

  if (!open) {
    return (
      <button type="button" className={styles.trigger} onClick={() => setOpen(true)}>
        회사 등록 요청하기
      </button>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <label className={styles.field}>
        <span className={styles.label}>회사 이름</span>
        <input
          className={styles.input}
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={200}
          required
        />
      </label>
      <label className={styles.field}>
        <span className={styles.label}>웹사이트 (선택)</span>
        <input
          type="url"
          className={styles.input}
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          maxLength={500}
          placeholder="https://"
        />
      </label>
      <label className={styles.field}>
        <span className={styles.label}>참고할 내용 (선택)</span>
        <textarea
          className={styles.textarea}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="채용 공고 링크나 정식 법인명을 적어 주시면 확인이 빨라집니다."
        />
      </label>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <button type="submit" className={styles.submit} disabled={submitting}>
        {submitting ? "보내는 중…" : "요청 보내기"}
      </button>
    </form>
  );
}
