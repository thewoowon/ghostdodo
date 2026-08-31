/**
 * Supporting brand marks — the field-guide vocabulary around the mascot.
 *
 * All original, all `currentColor`, all decorative by default (`aria-hidden`)
 * unless given a title. None of these may be replaced with emoji: docs/02 §3
 * forbids emoji as illustration anywhere in primary navigation, metric cards,
 * or empty states.
 */
import type { SVGProps } from "react";

type MarkProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  title?: string;
  size?: number;
};

function frame({ title, size = 24, ...props }: MarkProps) {
  return {
    viewBox: "0 0 24 24",
    width: size,
    height: size,
    fill: "none" as const,
    role: title ? ("img" as const) : undefined,
    "aria-hidden": title ? undefined : (true as const),
    xmlns: "http://www.w3.org/2000/svg",
    ...props,
  };
}

/** Response received — a signal that arrived. Concentric arcs, not a bell. */
export function ResponseSignal({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <circle cx="12" cy="17.5" r="2.4" fill="currentColor" />
      <path
        d="M7.6 13.6a6.2 6.2 0 0 1 8.8 0M4.4 10.2a10.7 10.7 0 0 1 15.2 0"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** No response — the same arcs, severed. Reads as absence, not as an error. */
export function SilenceSignal({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      {/* ResponseSignal's arcs, severed rather than crossed out. A slash
          reads as a prohibition; a broken transmission reads as absence,
          which is what the data actually says. */}
      <circle
        cx="12"
        cy="17.5"
        r="2.4"
        stroke="currentColor"
        strokeWidth="1.8"
        fill="none"
      />
      <path
        d="M7.7 13.5a6.2 6.2 0 0 1 2.4-1.5M16.3 13.5a6.2 6.2 0 0 0-2.4-1.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M4.5 10.1a10.7 10.7 0 0 1 3.3-2.4M19.5 10.1a10.7 10.7 0 0 0-3.3-2.4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.5"
      />
    </svg>
  );
}

/** Verified — a field stamp, not a checkmark badge. */
export function EvidenceStamp({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <path
        d="M12 2.6l2.6 1.7 3.1-.4 1 3 2.5 1.9-1.3 2.8.4 3.1-3 1-1.9 2.5-2.9-1.2-2.9 1.2-1.9-2.5-3-1 .4-3.1L3.8 8.8l2.5-1.9 1-3 3.1.4z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M8.9 11.4l2.2 2.2 4-4.4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Fossil — the extinction motif, used for long-dormant records. */
export function FossilMark({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <path
        d="M4.6 19.4c-1.4-1.4-1.4-3.6 0-5s3.6-1.4 5 0l4.4 4.4c1.4 1.4 1.4 3.6 0 5s-3.6 1.4-5 0z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M19.4 4.6c1.4 1.4 1.4 3.6 0 5s-3.6 1.4-5 0L10 5.2c-1.4-1.4-1.4-3.6 0-5s3.6-1.4 5 0z"
        stroke="currentColor"
        strokeWidth="1.7"
        opacity="0.55"
      />
      <path d="M9 15l6-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

/** Footprint — the observation trail motif used along the Ghostory. */
export function FootprintMark({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      {/* Three toes over a pad — a bird track, read top-down. */}
      <ellipse cx="6.6" cy="8.4" rx="1.9" ry="2.9" transform="rotate(-26 6.6 8.4)" fill="currentColor" />
      <ellipse cx="12" cy="6.6" rx="1.9" ry="3.1" fill="currentColor" />
      <ellipse cx="17.4" cy="8.4" rx="1.9" ry="2.9" transform="rotate(26 17.4 8.4)" fill="currentColor" />
      <ellipse cx="12" cy="16.4" rx="3.6" ry="4.2" fill="currentColor" />
    </svg>
  );
}

/** Timeline spine for the Ghostory — a bone, not a generic dotted rule. */
export function TimelineBone({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      {/* A bone: a shaft with two knobs at each end, drawn on the diagonal
          so it can tile down the Ghostory spine. */}
      <path
        d="M8.6 9.1l6.3 6.3"
        stroke="currentColor"
        strokeWidth="3.4"
        strokeLinecap="round"
      />
      <circle cx="6.3" cy="5.9" r="2.7" fill="currentColor" />
      <circle cx="5.9" cy="10.3" r="2.7" fill="currentColor" />
      <circle cx="17.7" cy="18.1" r="2.7" fill="currentColor" />
      <circle cx="18.1" cy="13.7" r="2.7" fill="currentColor" />
    </svg>
  );
}

/** Field notebook — the archive/record motif. */
export function FieldNotebook({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <path
        d="M6 3.4h11.4a1.6 1.6 0 0 1 1.6 1.6v14a1.6 1.6 0 0 1-1.6 1.6H6z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M6 3.4a1.8 1.8 0 0 0 0 3.6M6 7a1.8 1.8 0 0 0 0 3.6M6 10.6a1.8 1.8 0 0 0 0 3.6M6 14.2a1.8 1.8 0 0 0 0 3.6M6 17.8a1.8 1.8 0 0 0 0 2.8"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M10 8.4h5.4M10 12h5.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

/** Egg — used for newly added companies with no observations yet. */
export function DodoEgg({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <path
        d="M12 2.6c3.9 0 7 5 7 9.7a7 7 0 0 1-14 0c0-4.7 3.1-9.7 7-9.7z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M8.6 12.8l2.2-1.4 1 2.4 2.2-1.5 1.4 1.7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.6"
      />
    </svg>
  );
}

/** Observation ripple — the generic "we are watching" motif. */
export function RadarRipple({ title, size = 24, ...rest }: MarkProps) {
  return (
    <svg {...frame({ title, size, ...rest })}>
      {title ? <title>{title}</title> : null}
      <circle cx="12" cy="12" r="2.2" fill="currentColor" />
      <circle cx="12" cy="12" r="5.6" stroke="currentColor" strokeWidth="1.6" opacity="0.6" />
      <circle cx="12" cy="12" r="9.2" stroke="currentColor" strokeWidth="1.6" opacity="0.3" />
    </svg>
  );
}
