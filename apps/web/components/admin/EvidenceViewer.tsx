"use client";

import { useState } from "react";

import { apiRequest, ApiError } from "@/lib/api/client";
import { viewEvidence, type ModeratorEvidence } from "@/lib/api/admin";

import styles from "./EvidenceViewer.module.css";

type EvidenceRow = {
  id: string;
  kind: string;
  content_type: string;
  size_bytes: number | null;
  original_filename: string | null;
  review_state: string;
  access_state: string;
  created_at: string;
};

const REVIEW_STATE_LABELS: Record<string, string> = {
  PENDING: "검토 대기",
  CLEAN: "확인 완료",
  PII_SUSPECTED: "개인정보 의심",
  REDACTED: "일부 가림",
  REJECTED: "반려",
};

/**
 * Private evidence, opened deliberately.
 *
 * Nothing is fetched until a moderator clicks: requesting a signed URL writes
 * an access-log row server-side, so speculative prefetching would fill the
 * audit trail with views that never happened.
 */
export function EvidenceViewer({ reportId }: { reportId: string }) {
  const [rows, setRows] = useState<EvidenceRow[] | null>(null);
  const [opened, setOpened] = useState<Record<string, ModeratorEvidence>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function listEvidence() {
    setLoading(true);
    setError(null);
    try {
      setRows(await apiRequest<EvidenceRow[]>(`/reports/${reportId}/evidence`));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "자료 목록을 불러오지 못했습니다.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function open(evidenceId: string) {
    setError(null);
    try {
      const evidence = await viewEvidence(evidenceId);
      setOpened((current) => ({ ...current, [evidenceId]: evidence }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "자료를 열 수 없습니다.");
    }
  }

  if (rows === null) {
    return (
      <div className={styles.wrap}>
        <button
          type="button"
          className={styles.toggle}
          onClick={listEvidence}
          disabled={loading}
        >
          {loading ? "불러오는 중…" : "첨부 자료 확인"}
        </button>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <p className={styles.notice}>
        자료 열람은 감사 로그에 기록됩니다. 열람 링크는 몇 분 뒤 만료됩니다.
      </p>

      <ul className={styles.list}>
        {rows.map((row) => {
          const viewed = opened[row.id];
          return (
            <li key={row.id} className={styles.row}>
              <span className={styles.name}>
                {row.original_filename ?? row.kind}
                <span className={styles.state}>
                  {REVIEW_STATE_LABELS[row.review_state] ?? row.review_state}
                </span>
              </span>

              {viewed ? (
                <a
                  href={viewed.signed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.openLink}
                >
                  새 창에서 열기
                </a>
              ) : (
                <button
                  type="button"
                  className={styles.openButton}
                  onClick={() => open(row.id)}
                  disabled={row.access_state !== "AVAILABLE"}
                >
                  {row.access_state === "AVAILABLE" ? "열람" : "열람 불가"}
                </button>
              )}
            </li>
          );
        })}
      </ul>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
