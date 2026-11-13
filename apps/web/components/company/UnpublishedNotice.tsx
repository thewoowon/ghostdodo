import Link from "next/link";

import { DodoEgg } from "@/components/brand/svg/marks";

import styles from "./UnpublishedNotice.module.css";

/**
 * In place of a real company's record while the launch gate holds it back
 * (docs/08 §11). Says why, and that reporting still counts — the point of
 * listing the company before launch is that applicants can file now and
 * the record is there when publication opens.
 *
 * Neutral by design: no verdict colour, no count, nothing that hints at
 * what has or has not been filed.
 */
export function UnpublishedNotice({ compact = false }: { compact?: boolean }) {
  return (
    <section
      className={`${styles.notice} ${compact ? styles.compact : ""}`}
      aria-label="공개 준비 중"
    >
      <DodoEgg size={compact ? 22 : 28} className={styles.mark} />
      <div>
        <h2 className={styles.title}>공개 준비 중</h2>
        <p className={styles.body}>
          실제 기업의 기록은 개인정보 처리방침과 이용약관 검토를 마친 뒤
          공개합니다. 지금 남기는 기록도 검토를 거쳐 그대로 쌓이고, 공개가
          시작되면 함께 집계됩니다.
        </p>
        {!compact && (
          <Link href="/report/new" className={styles.link}>
            이 회사 경험 기록하기
          </Link>
        )}
      </div>
    </section>
  );
}
