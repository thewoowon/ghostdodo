import type { Metadata } from "next";

import { ReportWizard } from "@/components/report/ReportWizard";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "채용 경험 기록하기",
  // Private user flow — never indexed (docs/04 §5).
  robots: { index: false, follow: false },
};

export default function NewReportPage() {
  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>채용 경험 기록하기</h1>
        <p className={styles.lede}>
          겪은 일을 사실대로 남겨 주세요. 회사가 결과를 알려줬다면 그것도 똑같이
          중요한 기록입니다. 작성자 정보는 회사에도, 다른 이용자에게도 공개되지
          않습니다.
        </p>
      </header>
      <ReportWizard />
    </div>
  );
}
