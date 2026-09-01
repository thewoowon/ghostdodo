import styles from "./Wordmark.module.css";

/**
 * The GhostDodo wordmark.
 *
 * Two things make it a mark rather than a line of type:
 *
 * 1. Weight contrast. `Ghost` sits at 400 and `Dodo` at 800, so the bird —
 *    not the ghost — carries the emphasis.
 * 2. The two `o`s of `Dodo` are drawn here, not set. Each is an eye: the
 *    font's own ring with a pupil in the counter, echoing `DODO_EYE` in
 *    `svg/paths.ts`.
 *
 * The substitution only works because the drawn ring matches the real glyph.
 * These numbers are measured from Bricolage Grotesque at weight 800, in units
 * of 1/1000 em, and must be re-measured if the display face ever changes:
 *
 *   advance 567 · ink 525 × 560 · ring stem 167.5 · counter 190 · overshoot 14
 *
 * Ring stem is kept at the true 167.5 so the `o`s carry the same colour as the
 * `D` and `d` beside them. The one deliberate deviation is width: the ink is
 * widened 525 → 560, which opens the counter from 190 to 225 and buys the
 * pupil enough room to survive. At the header's 18px the counter is barely
 * 4px across, and at the true width the pupil closes up into a blob on a 1x
 * display — checked at 1x and 2x, 16px through 40px.
 */

/** Ink box of the drawn `o`, in 1/1000 em. Wider than the glyph by design. */
const INK_WIDTH = 560;
const INK_HEIGHT = 560;
/** Side bearings, carried over from the real glyph's 567 advance. */
const ADVANCE = INK_WIDTH + 42;
const RING_STEM = 167.5;
const PUPIL = 65;

const CENTER_X = ADVANCE / 2;
const CENTER_Y = INK_HEIGHT / 2;

function EyeO() {
  return (
    <svg
      viewBox={`0 0 ${ADVANCE} ${INK_HEIGHT}`}
      width={`${ADVANCE / 1000}em`}
      height={`${INK_HEIGHT / 1000}em`}
      className={styles.eye}
      fill="none"
      aria-hidden
    >
      {/* Stroke is centred on the path, so the path radius is the outer
          radius less half the stem. */}
      <ellipse
        cx={CENTER_X}
        cy={CENTER_Y}
        rx={INK_WIDTH / 2 - RING_STEM / 2}
        ry={INK_HEIGHT / 2 - RING_STEM / 2}
        stroke="currentColor"
        strokeWidth={RING_STEM}
      />
      <circle cx={CENTER_X} cy={CENTER_Y} r={PUPIL} fill="currentColor" />
    </svg>
  );
}

/**
 * Decorative by default: two of the nine letters are SVG, so the text layer
 * alone would announce "GhostDd". Callers give the surrounding link or heading
 * the accessible name instead — `SiteHeader` does this with `aria-label`.
 */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={className ? `${styles.wordmark} ${className}` : styles.wordmark}
      aria-hidden
    >
      <span className={styles.ghost}>Ghost</span>
      <span className={styles.dodo}>
        D<EyeO />d<EyeO />
      </span>
    </span>
  );
}
