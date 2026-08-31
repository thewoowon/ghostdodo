import { ResponseSignal, SilenceSignal } from "@/components/brand/svg/marks";

import styles from "./MetricCard.module.css";

type Props = {
  label: string;
  /** Already formatted, or null when the sample is too small to publish. */
  value: string | null;
  caption: string;
  tone?: "neutral" | "alive" | "extinct";
  icon?: "response" | "silence" | null;
};

/**
 * A single headline metric.
 *
 * When `value` is null the card shows `표본 부족` rather than a number. This
 * is the visual half of the suppression guarantee: the API refuses to compute
 * a small-sample rate, and this component refuses to imply one.
 */
export function MetricCard({
  label,
  value,
  caption,
  tone = "neutral",
  icon = null,
}: Props) {
  const suppressed = value === null;

  return (
    <div className={`${styles.card} ${styles[tone]}`}>
      <div className={styles.head}>
        <span className={styles.label}>{label}</span>
        {icon === "response" && <ResponseSignal size={16} className={styles.icon} />}
        {icon === "silence" && <SilenceSignal size={16} className={styles.icon} />}
      </div>

      {suppressed ? (
        <p className={styles.suppressed}>표본 부족</p>
      ) : (
        <p className={`${styles.value} gd-tabular`}>{value}</p>
      )}

      <p className={styles.caption}>{caption}</p>
    </div>
  );
}
