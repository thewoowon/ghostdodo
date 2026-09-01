/** Read helpers used by Server Components. */
import { apiRequest, companyTag } from "./client";
import type {
  CompanyDetail,
  CompanyMetrics,
  CompanySummary,
  JobCard,
  JobDetail,
  LedgerEntry,
  Methodology,
  OwnReport,
  Paged,
  Profile,
  PublicReportCard,
} from "./types";
import type { MetricWindow } from "@/lib/domain";

/** Public company data changes only when moderation acts, so cache it and
 *  revalidate by tag rather than polling. */
const PUBLIC_CACHE = { revalidate: 300 } as const;

export function searchCompanies(
  query: string,
  signal?: AbortSignal,
): Promise<CompanySummary[]> {
  const params = new URLSearchParams({ q: query });
  return apiRequest<CompanySummary[]>(`/companies/search?${params}`, {
    cache: "no-store",
    ...(signal ? { signal } : {}),
  });
}

export function getCompany(slug: string): Promise<CompanyDetail> {
  return apiRequest<CompanyDetail>(`/companies/${encodeURIComponent(slug)}`, {
    next: { ...PUBLIC_CACHE, tags: [companyTag(slug)] },
  });
}

export function getCompanyMetrics(
  slug: string,
  window: MetricWindow = "12m",
): Promise<CompanyMetrics> {
  const params = new URLSearchParams({ window });
  return apiRequest<CompanyMetrics>(
    `/companies/${encodeURIComponent(slug)}/metrics?${params}`,
    { next: { ...PUBLIC_CACHE, tags: [companyTag(slug)] } },
  );
}

export function getCompanyReports(
  slug: string,
  limit = 20,
): Promise<PublicReportCard[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest<PublicReportCard[]>(
    `/companies/${encodeURIComponent(slug)}/reports?${params}`,
    { next: { ...PUBLIC_CACHE, tags: [companyTag(slug)] } },
  );
}

/** Postings turn over faster than metrics, and an expired one should drop
 *  out of a listing within minutes rather than hours. */
const JOBS_CACHE = { revalidate: 120 } as const;

export function getJobs(
  options: { q?: string; company?: string; cursor?: string; limit?: number } = {},
): Promise<Paged<JobCard>> {
  const params = new URLSearchParams();
  if (options.q) params.set("q", options.q);
  if (options.company) params.set("company", options.company);
  if (options.cursor) params.set("cursor", options.cursor);
  if (options.limit) params.set("limit", String(options.limit));
  const query = params.toString();
  return apiRequest<Paged<JobCard>>(`/jobs${query ? `?${query}` : ""}`, {
    next: { ...JOBS_CACHE, tags: ["jobs"] },
  });
}

export function getJob(jobId: string): Promise<JobDetail> {
  return apiRequest<JobDetail>(`/jobs/${encodeURIComponent(jobId)}`, {
    next: { ...JOBS_CACHE, tags: ["jobs"] },
  });
}

export function getCompanyJobs(
  slug: string,
  options: { cursor?: string; limit?: number } = {},
): Promise<Paged<JobCard>> {
  const params = new URLSearchParams();
  if (options.cursor) params.set("cursor", options.cursor);
  if (options.limit) params.set("limit", String(options.limit));
  const query = params.toString();
  return apiRequest<Paged<JobCard>>(
    `/companies/${encodeURIComponent(slug)}/jobs${query ? `?${query}` : ""}`,
    { next: { ...JOBS_CACHE, tags: ["jobs", companyTag(slug)] } },
  );
}

/** The signed-in user's own reports, including ones still under review.
 *  Never cached — a moderation decision must show up on the next load. */
export function getMyReports(cookie?: string): Promise<OwnReport[]> {
  return apiRequest<OwnReport[]>("/me/reports", {
    cache: "no-store",
    ...(cookie ? { cookie } : {}),
  });
}

function mine<T>(path: string, cookie?: string): Promise<T> {
  return apiRequest<T>(path, {
    cache: "no-store",
    ...(cookie ? { cookie } : {}),
  });
}

export function getProfile(cookie?: string): Promise<Profile> {
  return mine<Profile>("/me", cookie);
}

export function getReputationLedger(cookie?: string): Promise<LedgerEntry[]> {
  return mine<LedgerEntry[]>("/me/reputation", cookie);
}

export function getCreditLedger(cookie?: string): Promise<LedgerEntry[]> {
  return mine<LedgerEntry[]>("/me/credits", cookie);
}

export function getMethodology(): Promise<Methodology> {
  // Methodology changes require a version bump and a deploy, so it can be
  // cached hard.
  return apiRequest<Methodology>("/methodology", {
    next: { revalidate: 3600, tags: ["methodology"] },
  });
}
