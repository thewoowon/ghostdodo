import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";

import styles from "./SiteHeader.module.css";

/** Minimal header — the landing page's visual anchor is the search bar, not
 *  the navigation (docs/03 §2). No emoji in navigation (docs/02 §3). */
export function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={`gd-shell ${styles.inner}`}>
        <Link href="/" className={styles.brand} aria-label="GhostDodo 홈">
          <DodoMark size={30} className={styles.mark} />
          <span className={styles.wordmark}>GhostDodo</span>
        </Link>

        <nav className={styles.nav} aria-label="주요 메뉴">
          <Link href="/dex" className={styles.navLink}>
            도감
          </Link>
          <Link href="/methodology" className={styles.navLink}>
            측정 기준
          </Link>
          <Link href="/report/new" className={styles.cta}>
            기록하기
          </Link>
        </nav>
      </div>
    </header>
  );
}
