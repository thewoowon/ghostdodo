import { RANK_LABELS, REPUTATION_RANKS, type ReputationRank } from "@/lib/domain";

import styles from "./RankCrest.module.css";

/**
 * The rank crest.
 *
 * Original geometry, drawn here rather than assembled from an icon set or an
 * emoji (docs/02 §3). A field-guide seal: a notched ring with one tick per
 * tier, filled up to the rank held. The shape is identical at every rank so
 * the crest reads as one family, and only the filled ticks change — standing
 * should look earned, not like a different badge each time.
 */
export function RankCrest({ rank, size = 68 }: { rank: ReputationRank; size?: number }) {
  const tier = Math.max(0, REPUTATION_RANKS.indexOf(rank));
  const label = RANK_LABELS[rank] ?? rank;

  // Ticks sit on the upper arc, swept clockwise from the left shoulder.
  const ticks = REPUTATION_RANKS.map((_, index) => {
    const spread = 200; // degrees covered by the arc
    const start = 170;
    const angle = ((start + (spread / (REPUTATION_RANKS.length - 1)) * index) * Math.PI) / 180;
    return {
      x: 34 + Math.cos(angle) * 25,
      y: 34 + Math.sin(angle) * 25,
      filled: index <= tier,
    };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 68 68"
      className={styles.crest}
      role="img"
      aria-label={`${label} 등급`}
    >
      <circle cx="34" cy="34" r="31" className={styles.ring} />
      <circle cx="34" cy="34" r="20" className={styles.field} />
      {/* A single feather-quill stroke: the archive's own mark, not a star
          or a shield borrowed from a game UI. */}
      <path d="M27 41c4-11 9-16 15-18-1 8-5 14-11 17l-4 1z" className={styles.quill} />
      <path d="M27 41l-3 4" className={styles.quillStem} />
      {ticks.map((tick, index) => (
        <circle
          key={index}
          cx={tick.x}
          cy={tick.y}
          r={tick.filled ? 2.6 : 1.6}
          className={tick.filled ? styles.tickOn : styles.tickOff}
        />
      ))}
    </svg>
  );
}
