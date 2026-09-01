import type { LedgerEntry } from "@/lib/api/types";
import { CREDIT_EVENT_LABELS, REPUTATION_EVENT_LABELS } from "@/lib/domain";
import { formatShortDate } from "@/lib/format/metrics";

import styles from "./LedgerList.module.css";

type Props = {
  entries: LedgerEntry[];
  kind: "reputation" | "credit";
};

/**
 * An append-only ledger, shown as one.
 *
 * Every line carries its own delta and the balance it produced, so the
 * current number is always explainable from the rows above it — the same
 * auditability the API guarantees (docs/07 §2). Nothing here is editable and
 * nothing is collapsed into a summary.
 */
export function LedgerList({ entries, kind }: Props) {
  const labels = kind === "credit" ? CREDIT_EVENT_LABELS : REPUTATION_EVENT_LABELS;

  if (entries.length === 0) {
    return (
      <p className={styles.empty}>
        {kind === "credit"
          ? "아직 크레딧 내역이 없습니다."
          : "아직 평판 내역이 없습니다. 기록을 남기면 이곳에 쌓입니다."}
      </p>
    );
  }

  return (
    <ul className={styles.list}>
      {entries.map((entry) => (
        <li key={entry.id} className={styles.row}>
          <span className={styles.label}>
            {labels[entry.event_type] ?? entry.event_type}
          </span>
          <span className={styles.date}>{formatShortDate(entry.created_at) ?? ""}</span>
          <span
            className={`${styles.delta} gd-tabular ${
              entry.delta < 0 ? styles.down : styles.up
            }`}
          >
            {entry.delta > 0 ? `+${entry.delta}` : entry.delta}
          </span>
          <span className={`${styles.balance} gd-tabular`}>{entry.balance_after}</span>
        </li>
      ))}
    </ul>
  );
}
