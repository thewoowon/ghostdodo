/** Read helpers used by Server Components. */
import { apiRequest, companyTag } from "./client";
import type {
  CompanyDetail,
  CompanyMetrics,
  CompanySummary,
  Methodology,
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

export function getMethodology(): Promise<Methodology> {
  // Methodology changes require a version bump and a deploy, so it can be
  // cached hard.
  return apiRequest<Methodology>("/methodology", {
    next: { revalidate: 3600, tags: ["methodology"] },
  });
}
