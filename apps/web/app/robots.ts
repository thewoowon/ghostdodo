import type { MetadataRoute } from "next";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private user surfaces are never indexed (docs/04 §5).
      // `/api` is the API proxied onto this origin — a crawlable surface by
      // accident of the single-origin layout, and never a page.
      disallow: [
        "/me",
        "/report",
        "/admin",
        "/company-portal",
        "/search",
        "/api",
      ],
    },
    sitemap: `${APP_URL}/sitemap.xml`,
  };
}
