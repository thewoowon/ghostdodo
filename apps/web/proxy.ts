import { NextResponse, type NextRequest } from "next/server";

import { visitorIp, vouchFor } from "@/lib/api/visitor";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

/**
 * `/api/v1/*` → the API, naming the visitor on the way.
 *
 * This is the same one-origin rewrite as `next.config.ts` (which stays as the
 * fallback), done here so the request headers can be changed in the same
 * step: a header override from `NextResponse.next()` is not something to
 * rely on surviving into a later rewrite to an external host. See
 * `lib/api/visitor.ts` for why the API needs to be told who the visitor is.
 */
export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  vouchFor(headers, visitorIp(request.headers));

  const { pathname, search } = request.nextUrl;
  return NextResponse.rewrite(new URL(`${pathname}${search}`, API_ORIGIN), {
    request: { headers },
  });
}

export const config = {
  matcher: "/api/v1/:path*",
};
