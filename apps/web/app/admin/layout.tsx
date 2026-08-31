import type { Metadata } from "next";
import Link from "next/link";

import styles from "./layout.module.css";

export const metadata: Metadata = {
  title: "운영 콘솔",
  // Never indexed, and never linked from public navigation.
  robots: { index: false, follow: false },
};

export default function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className={`gd-shell ${styles.shell}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>운영 콘솔</h1>
        <nav className={styles.nav} aria-label="운영 메뉴">
          <Link href="/admin/reports">기록 검토</Link>
          <Link href="/admin/disputes">정정 요청</Link>
        </nav>
      </header>
      <p className={styles.notice}>
        이곳의 모든 결정은 감사 로그에 기록되며, 회사 지표가 즉시 다시
        계산됩니다. 첨부 자료 열람 역시 열람자와 시각이 기록됩니다.
      </p>
      {children}
    </div>
  );
}
