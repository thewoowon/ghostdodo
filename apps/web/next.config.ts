import type { NextConfig } from "next";

/**
 * The API's origin as this server must reach it.
 *
 * Production runs one public origin: Vercel serves the app and rewrites
 * `/api/v1/*` to the API on Railway. That is what keeps the session cookie
 * host-only and same-site, and it is why the browser never learns the API's
 * real address.
 */
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

// On Vercel the fallback would proxy production traffic to a localhost that
// does not exist, and every API call would 502 with no obvious cause. Fail
// the build instead — a missing env var is cheaper to find here.
if (process.env.VERCEL && !process.env.API_ORIGIN) {
  throw new Error(
    "API_ORIGIN is required on Vercel: the /api/v1 rewrite has nowhere to go.",
  );
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  typedRoutes: true,
  experimental: {
    // Company pages are the SEO surface; keep their payload small.
    optimizePackageImports: [],
  },
  async rewrites() {
    return [
      {
        // One origin, so `Set-Cookie` from the API lands on this host and
        // CORS never enters the picture. Everything the browser sends —
        // fetches, and the Google sign-in navigation that leaves the app —
        // goes through here.
        source: "/api/v1/:path*",
        destination: `${API_ORIGIN}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
      {
        // Private user surfaces must never be indexed (docs/04 §5).
        source: "/(me|report|admin)/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
      {
        // The API is a proxied path on this origin now, so it inherits the
        // site's headers. It must never be indexed or cached at the edge.
        source: "/api/:path*",
        headers: [
          { key: "X-Robots-Tag", value: "noindex, nofollow" },
          { key: "Cache-Control", value: "no-store" },
        ],
      },
    ];
  },
};

export default nextConfig;
