/**
 * Posting presentation rules.
 *
 * Closing dates are Korean calendar dates, so every comparison here happens
 * in Asia/Seoul rather than in the viewer's timezone — a posting that closes
 * today must not read as 마감 to someone browsing from Berlin at 9pm.
 */
import type { ApplicationSource, EmploymentType, RoleCategory } from "@/lib/domain";
import { EMPLOYMENT_LABELS, ROLE_LABELS, SOURCE_LABELS } from "@/lib/domain";

/** Today in Seoul, as `YYYY-MM-DD` — the same shape the API sends. */
export function seoulToday(now: Date = new Date()): string {
  // en-CA formats as YYYY-MM-DD, which sorts and subtracts without parsing
  // through a timezone a second time.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

function daysBetween(from: string, to: string): number | null {
  const start = Date.parse(`${from}T00:00:00Z`);
  const end = Date.parse(`${to}T00:00:00Z`);
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return Math.round((end - start) / 86_400_000);
}

export type JobClosing =
  | { kind: "closed"; label: string }
  | { kind: "always"; label: string }
  | { kind: "today"; label: string }
  | { kind: "soon"; label: string; days: number }
  | { kind: "dated"; label: string };

/**
 * How a posting's deadline should read.
 *
 * `is_open` comes from the API, which owns the decision; this only chooses
 * the words. A closed posting says so plainly rather than disappearing —
 * someone who followed a shared link deserves an explanation.
 */
export function jobClosing(
  job: { closes_on: string | null; is_open: boolean },
  today: string = seoulToday(),
): JobClosing {
  if (!job.is_open) return { kind: "closed", label: "마감된 공고" };
  if (job.closes_on === null) return { kind: "always", label: "상시 채용" };

  const remaining = daysBetween(today, job.closes_on);
  if (remaining === null) return { kind: "always", label: "상시 채용" };
  if (remaining <= 0) return { kind: "today", label: "오늘 마감" };
  if (remaining <= 7) {
    return { kind: "soon", label: `마감 D-${remaining}`, days: remaining };
  }
  return { kind: "dated", label: `${job.closes_on} 마감` };
}

/**
 * Where the posting came from.
 *
 * Source attribution stays on every card (docs/09 Phase 6 acceptance) —
 * GhostDodo did not write the posting and must not look like it did.
 */
export function sourceName(job: {
  source: ApplicationSource;
  source_label: string | null;
}): string {
  return job.source_label ?? SOURCE_LABELS[job.source];
}

/** Role and employment type, skipping whichever the posting did not record. */
export function jobFacets(job: {
  role_category: RoleCategory | null;
  employment_type: EmploymentType | null;
  location: string | null;
}): string[] {
  return [
    job.role_category ? ROLE_LABELS[job.role_category] : null,
    job.employment_type ? EMPLOYMENT_LABELS[job.employment_type] : null,
    job.location,
  ].filter((facet): facet is string => Boolean(facet));
}
