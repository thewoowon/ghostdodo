import type { MetadataRoute } from "next";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private user surfaces are never indexed (docs/04 §5).
      disallow: ["/me", "/report", "/admin", "/company-portal", "/search"],
    },
    sitemap: `${APP_URL}/sitemap.xml`,
  };
}
