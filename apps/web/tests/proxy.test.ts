// @vitest-environment node
/**
 * Naming the visitor to the API.
 *
 * In production Railway's edge replaces X-Forwarded-For with Vercel's
 * address, so the API could not tell visitors apart and every rate limit
 * was shared site-wide. The proxy now names the visitor in its own header
 * and vouches for it with a shared secret. What matters: the pair is sent
 * only when there is a secret, a browser can never smuggle its own pair
 * through, and the rewrite still lands on the API with the query intact.
 */
import { getRewrittenUrl, isRewrite } from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "@/proxy";
import { CLIENT_IP_HEADER, PROXY_SECRET_HEADER, visitorIp } from "@/lib/api/visitor";

const SECRET = "s".repeat(40);

/** What the API will receive: Next carries request-header overrides on
 *  the response as `x-middleware-request-<name>`. */
function forwarded(response: Response, name: string): string | null {
  return response.headers.get(`x-middleware-request-${name.toLowerCase()}`);
}

function request(headers: Record<string, string> = {}) {
  return new NextRequest("https://ghostdodo.com/api/v1/companies/search?q=%EB%8F%84%EB%8F%84", {
    headers,
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("proxy", () => {
  it("rewrites to the API with the path and query intact", () => {
    const response = proxy(request());

    expect(isRewrite(response)).toBe(true);
    expect(getRewrittenUrl(response)).toBe(
      "http://localhost:8000/api/v1/companies/search?q=%EB%8F%84%EB%8F%84",
    );
  });

  it("names the visitor and vouches for it when a secret is configured", () => {
    vi.stubEnv("PROXY_SHARED_SECRET", SECRET);
    const response = proxy(request({ "x-real-ip": "203.0.113.5" }));

    expect(forwarded(response, CLIENT_IP_HEADER)).toBe("203.0.113.5");
    expect(forwarded(response, PROXY_SECRET_HEADER)).toBe(SECRET);
  });

  it("never passes a browser's own pair through", () => {
    // Someone hitting ghostdodo.com directly with the API's headers set.
    vi.stubEnv("PROXY_SHARED_SECRET", SECRET);
    const response = proxy(
      request({
        "x-real-ip": "203.0.113.5",
        [CLIENT_IP_HEADER]: "9.9.9.9",
        [PROXY_SECRET_HEADER]: "guess",
      }),
    );

    expect(forwarded(response, CLIENT_IP_HEADER)).toBe("203.0.113.5");
    expect(forwarded(response, PROXY_SECRET_HEADER)).toBe(SECRET);
  });

  it("sends neither header without a secret, stripping any the browser sent", () => {
    vi.stubEnv("PROXY_SHARED_SECRET", "");
    const response = proxy(
      request({ "x-real-ip": "203.0.113.5", [CLIENT_IP_HEADER]: "9.9.9.9" }),
    );

    expect(forwarded(response, CLIENT_IP_HEADER)).toBeNull();
    expect(forwarded(response, PROXY_SECRET_HEADER)).toBeNull();
  });
});

describe("visitorIp", () => {
  it("prefers x-real-ip, which Vercel sets itself", () => {
    const headers = new Headers({ "x-real-ip": "203.0.113.5", "x-forwarded-for": "1.1.1.1" });
    expect(visitorIp(headers)).toBe("203.0.113.5");
  });

  it("falls back to the first x-forwarded-for entry", () => {
    const headers = new Headers({ "x-forwarded-for": "203.0.113.5, 10.0.0.1" });
    expect(visitorIp(headers)).toBe("203.0.113.5");
  });

  it("is null when nothing names the visitor", () => {
    expect(visitorIp(new Headers())).toBeNull();
  });
});
