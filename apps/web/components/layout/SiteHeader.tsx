import Link from "next/link";

import { SessionNav } from "@/components/auth/SessionNav";
import { DodoMark } from "@/components/brand/svg/DodoMark";
import { Wordmark } from "@/components/brand/Wordmark";

import styles from "./SiteHeader.module.css";

/** Minimal header — the landing page's visual anchor is the search bar, not
 *  the navigation (docs/03 §2). No emoji in navigation (docs/02 §3). */
export function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={`gd-shell ${styles.inner}`}>
        <Link href="/" className={styles.brand} aria-label="GhostDodo 홈">
          <DodoMark size={30} className={styles.mark} />
          <Wordmark className={styles.wordmark} />
        </Link>

        <nav className={styles.nav} aria-label="주요 메뉴">
          <Link href="/jobs" className={styles.navLink}>
            채용공고
          </Link>
          <Link href="/dex" className={styles.navLink}>
            도감
          </Link>
          <Link href="/methodology" className={styles.navLink}>
            측정 기준
          </Link>
          <SessionNav />
          <Link href="/report/new" className={styles.cta}>
            기록하기
          </Link>
        </nav>
      </div>
    </header>
  );
}
