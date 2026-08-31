/**
 * Regression guard for a bug that is invisible in English.
 *
 * Next passes dynamic route params percent-encoded but query params decoded.
 * Encoding an already-encoded slug yields `%25EA%25B7%25B8…` and a 404 that
 * only ever appears for non-ASCII slugs — which, for Korean company names,
 * is nearly all of them.
 */
import { describe, expect, it } from "vitest";

import { decodeRouteParam } from "@/lib/route-params";

describe("decodeRouteParam", () => {
  it("decodes a percent-encoded Korean slug", () => {
    expect(decodeRouteParam("%EA%B7%B8%EB%A6%B0%ED%85%8C%ED%81%AC")).toBe("그린테크");
  });

  it("leaves an ASCII slug untouched", () => {
    expect(decodeRouteParam("dodolab")).toBe("dodolab");
  });

  it("survives a malformed escape sequence instead of throwing", () => {
    // A bad URL should 404, not crash the route.
    expect(decodeRouteParam("%E0%A4%A")).toBe("%E0%A4%A");
  });

  it("round-trips: encoding the decoded value reproduces the input", () => {
    const encoded = "%EA%B7%B8%EB%A6%B0%ED%85%8C%ED%81%AC";
    expect(encodeURIComponent(decodeRouteParam(encoded))).toBe(encoded);
  });
});
