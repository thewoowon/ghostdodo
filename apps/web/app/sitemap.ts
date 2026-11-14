import type { MetadataRoute } from "next";

import { jobsEnabled } from "@/lib/features";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

/**
 * Static routes only, for now.
 *
 * Company pages are the growth engine and belong here, but listing them
 * requires a paginated public company endpoint. Emitting a partial or stale
 * company list would be worse than emitting none.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const routes = [
    { path: "", priority: 1 },
    { path: "/about", priority: 0.6 },
    { path: "/methodology", priority: 0.8 },
    ...(jobsEnabled() ? [{ path: "/jobs", priority: 0.7 }] : []),
    { path: "/dex", priority: 0.7 },
    { path: "/policy/reporting", priority: 0.5 },
    { path: "/policy/verification", priority: 0.5 },
    { path: "/policy/privacy", priority: 0.4 },
    { path: "/policy/terms", priority: 0.4 },
  ];

  const lastModified = new Date();
  return routes.map(({ path, priority }) => ({
    url: `${APP_URL}${path}`,
    lastModified,
    changeFrequency: "weekly" as const,
    priority,
  }));
}
