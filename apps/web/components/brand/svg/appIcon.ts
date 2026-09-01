/**
 * App icon artwork — favicon, Apple touch icon, and the .ico entries.
 *
 * Built from the same `paths.ts` geometry as `DodoMark`, so the icon cannot
 * drift from the mascot. Nothing here re-authors a path; it only frames one.
 *
 * The icon is a filled tile rather than a bare silhouette on purpose. A tab
 * strip can be light or dark and a favicon gets no say in it, so the mark
 * carries its own ground instead of hoping for contrast.
 */
// Explicit extension so `scripts/generate-app-icons.mjs` can import this
// module under Node's type stripping, which does no extension resolution.
import { DODO_BEAK, DODO_BODY, DODO_EYE } from "./paths.ts";

type Frame = { x: number; y: number; width: number; height: number };

/**
 * Ink bounds of `DODO_BODY` + `DODO_BEAK` inside the 64×64 viewBox, measured
 * from the rendered paths. The mascot does not fill its own box — it sits low
 * and to the left — so the icon has to re-frame it or the artwork shrinks into
 * a corner.
 */
const FULL: Frame = { x: 4.4, y: 6, width: 47.4, height: 53.2 };

/**
 * Head and beak, with the body running off the bottom of the tile.
 *
 * At 16px the whole bird is about eleven pixels tall and the ghost hem and the
 * beak dissolve together into a rounded blob. Cropping to the identifying
 * feature — the oversized hooked beak, docs/02 §3 — is what keeps a 16px tab
 * icon legible. Same trade `DETAIL_THRESHOLD_PX` makes in `DodoMark`.
 */
const COMPACT: Frame = { x: 4.4, y: 6, width: 49.1, height: 34 };

/** Below this the full silhouette stops resolving and the crop takes over. */
export const COMPACT_BELOW_PX = 24;

/** Brand colours, mirrored from `styles/tokens.css` (`--gd-accent`, `--gd-paper`). */
const TILE = "#0f6b62";
const KNOCKOUT = "#faf8f5";

const BOX = 64;
const CORNER = 12;

/**
 * The eye is opened from the mascot's 3.2. At the mascot's own ratio it is
 * under a pixel at 16px and fills in, taking the bird's only piece of interior
 * detail with it. Checked at 16, 32, 48 and 180.
 */
const EYE_FULL = 4.5;
const EYE_COMPACT = 5;

export function appIconSvg(size: number): string {
  const compact = size < COMPACT_BELOW_PX;
  const frame = compact ? COMPACT : FULL;
  const padding = compact ? 4 : 8;
  const eye = compact ? EYE_COMPACT : EYE_FULL;

  const scale = (BOX - padding * 2) / Math.max(frame.width, frame.height);
  const x = BOX / 2 - scale * (frame.x + frame.width / 2);
  const y = BOX / 2 - scale * (frame.y + frame.height / 2);
  const place = `translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${scale.toFixed(4)})`;

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${BOX} ${BOX}" width="${size}" height="${size}">`,
    // The compact frame lets the body overrun the tile, so the tile is a clip
    // rather than a backdrop. Applied at every size to keep one composition.
    `<defs><clipPath id="gd-tile"><rect width="${BOX}" height="${BOX}" rx="${CORNER}"/></clipPath></defs>`,
    `<g clip-path="url(#gd-tile)">`,
    `<rect width="${BOX}" height="${BOX}" fill="${TILE}"/>`,
    `<g transform="${place}" fill="${KNOCKOUT}">`,
    `<path d="${DODO_BODY}"/>`,
    `<path d="${DODO_BEAK}"/>`,
    `</g>`,
    // Punched in the tile colour so the eye is a hole in the bird, not a dot
    // on top of it — the same relationship `DodoMark` has with the page.
    `<g transform="${place}">`,
    `<circle cx="${DODO_EYE.cx}" cy="${DODO_EYE.cy}" r="${eye}" fill="${TILE}"/>`,
    `</g>`,
    `</g>`,
    `</svg>`,
  ].join("");
}

/** Data URI form, for rasterisers that take an image rather than markup. */
export function appIconDataUri(size: number): string {
  return `data:image/svg+xml;base64,${Buffer.from(appIconSvg(size)).toString("base64")}`;
}
