import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";
import { Wordmark } from "@/components/brand/Wordmark";

import { SiteNav } from "./SiteNav";
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

        <SiteNav />
      </div>
    </header>
  );
}
