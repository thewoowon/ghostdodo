/**
 * GhostDodo mascot mark.
 *
 * Original artwork authored as SVG paths in this repository (see `paths.ts`).
 * Per docs/02 §3 it is deliberately distinct from any existing commercial
 * mascot: the identifying combination is an oversized hooked beak above a
 * notched ghost hem, with flat deadpan eyes and no idle motion.
 *
 * Renders in `currentColor`, so the same component serves as outline, filled
 * silhouette, and monochrome favicon.
 */
import type { SVGProps } from "react";

import {
  DETAIL_THRESHOLD_PX,
  DODO_BEAK,
  DODO_BEAK_SEAM,
  DODO_BODY,
  DODO_EYE,
} from "./paths";

export type DodoVariant = "filled" | "outline" | "silhouette";

export type DodoMarkProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  /**
   * Accessible name. Omit for decorative marks, which are then hidden from
   * assistive technology rather than announced as meaningless images.
   */
  title?: string;
  variant?: DodoVariant;
  size?: number;
  /** Background the eye is punched against. Defaults to the page ground. */
  eyeColor?: string;
};

export function DodoMark({
  title,
  variant = "filled",
  size = 64,
  eyeColor = "var(--gd-paper)",
  ...props
}: DodoMarkProps) {
  const decorative = !title;
  const outlined = variant === "outline";
  const showDetail = size >= DETAIL_THRESHOLD_PX;

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative || undefined}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      {title ? <title>{title}</title> : null}
      <g
        fill={outlined ? "none" : "currentColor"}
        stroke={outlined ? "currentColor" : "none"}
        strokeWidth={outlined ? 3 : 0}
        strokeLinejoin="round"
      >
        <path d={DODO_BODY} />
        <path d={DODO_BEAK} />
      </g>
      {!outlined && showDetail && (
        <path
          d={DODO_BEAK_SEAM}
          stroke={eyeColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          opacity={0.45}
        />
      )}
      {variant !== "silhouette" && (
        <>
          <circle cx={DODO_EYE.cx} cy={DODO_EYE.cy} r={DODO_EYE.r} fill={eyeColor} />
          <circle
            cx={DODO_EYE.cx}
            cy={DODO_EYE.cy}
            r={DODO_EYE.pupil}
            fill={outlined ? "currentColor" : "currentColor"}
          />
        </>
      )}
    </svg>
  );
}
