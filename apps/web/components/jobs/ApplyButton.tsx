"use client";

import { useCallback } from "react";

import { apiRequest } from "@/lib/api/client";

import styles from "./ApplyButton.module.css";

type Props = {
  jobId: string;
  applyUrl: string | null;
  isOpen: boolean;
  /** `primary` on a job detail page, `compact` inside a card list. */
  variant?: "primary" | "compact";
};

/**
 * `지원하러 가기` — the outbound deep link.
 *
 * GhostDodo never hosts an application, so this is a real anchor to the
 * employer or job board: middle-click, copy-link, and open-in-new-tab all
 * behave the way a link should. The click is counted alongside the
 * navigation, never in front of it — accounting that could keep someone from
 * applying would be worse than accounting that occasionally misses one.
 */
export function ApplyButton({ jobId, applyUrl, isOpen, variant = "primary" }: Props) {
  const record = useCallback(() => {
    apiRequest(`/jobs/${encodeURIComponent(jobId)}/outbound-click`, {
      method: "POST",
      body: { referrer_path: window.location.pathname },
      // The browser is navigating; without this the request is cancelled
      // whenever the link opens in the same tab.
      keepalive: true,
    }).catch(() => {
      // Deliberately silent. The user is already on their way to the posting.
    });
  }, [jobId]);

  if (!isOpen) {
    return (
      <span className={`${styles.inert} ${styles[variant]}`}>마감된 공고</span>
    );
  }

  if (applyUrl === null) {
    return (
      <span className={`${styles.inert} ${styles[variant]}`}>
        지원 링크 확인 중
      </span>
    );
  }

  return (
    <a
      href={applyUrl}
      target="_blank"
      // noreferrer keeps the referring path out of the employer's analytics;
      // what GhostDodo counts stays with GhostDodo.
      rel="noopener noreferrer nofollow"
      className={`${styles.button} ${styles[variant]}`}
      onClick={record}
      onAuxClick={record}
    >
      지원하러 가기
      <span className={styles.external} aria-hidden>
        ↗
      </span>
      <span className="gd-sr-only">(새 탭에서 외부 사이트로 이동)</span>
    </a>
  );
}
