/**
 * Shared GhostDodo path geometry.
 *
 * Centralized so the silhouette is authored once and reused across the mark,
 * the empty states, the favicon, and the share cards — docs/04 §8 forbids
 * duplicating large inline paths across the tree.
 *
 * Coordinates are for a 64×64 viewBox.
 */

/** Body: rounded head, tapering torso, ghost hem instead of feet. */
export const DODO_BODY =
  "M37 6c-9.7 0-16.5 7.4-16.5 16.6 0 2.6.4 4.4.4 6.6 0 4.6-2.4 7.6-2.4 12.9 0 4.7 " +
  "1.7 7.6 1.7 10.8 0 2-.9 3.4-.9 4.8 0 1 .7 1.5 1.6 1.5 2 0 3.1-2.5 4.8-2.5 1.6 0 " +
  "2.6 2.5 4.6 2.5s3-2.5 4.7-2.5c1.7 0 2.7 2.5 4.7 2.5s3-2.5 4.7-2.5c1.8 0 2.9 2.5 " +
  "4.9 2.5 1 0 1.7-.6 1.7-1.6 0-1.5-1-2.9-1-4.9 0-3.3 1.8-6.2 1.8-11.1 0-5.4-2.5-8.4-" +
  "2.5-12.9 0-2.2.4-4 .4-6.6C53.5 13.4 46.7 6 37 6z";

/**
 * Oversized hooked beak — the identifying feature of the silhouette.
 * Authored as ONE closed path (upper edge → tip → hook → lower edge) so it
 * renders seamlessly rather than showing a join at small sizes.
 */
export const DODO_BEAK =
  "M22 18.6C13.2 19.5 4.4 24.3 4.4 28.9c0 1.6 1 2.9 2.6 3.7" +
  "-.9 2.4-.3 5.2 1.7 6.9.9.8 2.1 1.2 3.2 1.1" +
  "-2.1-2-3-4.8-2.6-7.5 1.2.3 2.6.4 4.1.3l8.6-.6z";

/** Mandible seam. Detail only — omitted below ~64px where it turns to mush. */
export const DODO_BEAK_SEAM = "M7.4 26.8c3.7-2.3 9-4.2 14.4-4.9";

export const DODO_EYE = { cx: 34, cy: 20, r: 3.2, pupil: 1.4 } as const;

/** Below this rendered size, fine detail is dropped. */
export const DETAIL_THRESHOLD_PX = 56;
