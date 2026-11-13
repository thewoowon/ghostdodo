import type { Metadata } from "next";
import Link from "next/link";

import { QuickLog } from "@/components/report/QuickLog";

import styles from "../new/page.module.css";

export const metadata: Metadata = {
  title: "여러 회사 한 번에 기록하기",
  // Private user flow — never indexed (docs/04 §5).
  robots: { index: false, follow: false },
};

export default function QuickLogPage() {
  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>여러 회사 한 번에 기록하기</h1>
        <p className={styles.lede}>
          지원한 회사마다 한 줄씩 남겨 주세요. 결과를 알려준 회사도 똑같이 중요한
          기록입니다. 자세한 사정이나 첨부 자료는{" "}
          <Link href="/report/new">한 곳씩 기록하기</Link>에서 남길 수 있습니다.
        </p>
      </header>
      <QuickLog />
    </div>
  );
}
