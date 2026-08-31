import type { ResponseVerdict } from "@/lib/format/metrics";

import styles from "./VerdictBadge.module.css";

/**
 * The company's current response-behaviour verdict.
 *
 * Positive verdicts are styled with the same confidence as negative ones:
 * `답장 생존` is not a muted grey "fine", it is a decisive green. Neutrality
 * here is a product requirement, not a stylistic preference (README §3).
 */
export function VerdictBadge({ verdict }: { verdict: ResponseVerdict }) {
  return (
    <div className={`${styles.badge} ${styles[verdict.tone]}`}>
      <span className={styles.dot} aria-hidden />
      <span className={styles.label}>{verdict.label}</span>
    </div>
  );
}
