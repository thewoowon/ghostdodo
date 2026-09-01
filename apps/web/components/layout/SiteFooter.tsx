import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";

import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={`gd-shell ${styles.inner}`}>
        <div className={styles.brandBlock}>
          <DodoMark size={26} className={styles.mark} />
          <p className={styles.tagline}>답장이 멸종된 회사들을 기록합니다.</p>
        </div>

        <nav className={styles.links} aria-label="푸터 메뉴">
          <Link href="/methodology">측정 기준</Link>
          <Link href="/policy/reporting">기록 정책</Link>
          <Link href="/policy/verification">검증 정책</Link>
          <Link href="/policy/privacy">개인정보처리방침</Link>
          <Link href="/policy/terms">이용약관</Link>
          <Link href="/about">소개</Link>
        </nav>

        <p className={styles.note}>
          고스트도도는 채용 커뮤니케이션 기록 데이터베이스입니다. 특정 기업이나
          개인을 비방하기 위한 서비스가 아니며, 모든 지표는 표본 수와 기간을
          함께 표시합니다.
        </p>
      </div>
    </footer>
  );
}
