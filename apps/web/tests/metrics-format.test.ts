/**
 * Guards the presentation half of the sample-suppression rule.
 *
 * If these break, the UI has started rendering a number where the API
 * deliberately refused to compute one.
 */
import { describe, expect, it } from "vitest";

import {
  canPublishRates,
  formatDays,
  formatRate,
  responseVerdict,
} from "@/lib/format/metrics";

describe("formatRate", () => {
  it("returns null for a suppressed rate rather than a zero", () => {
    // The critical case: null must not become "0%".
    expect(formatRate(null)).toBeNull();
    expect(formatRate(undefined)).toBeNull();
  });

  it("formats a real rate as a whole percentage", () => {
    expect(formatRate(0.9118)).toBe("91%");
    expect(formatRate(0)).toBe("0%");
    expect(formatRate(1)).toBe("100%");
  });

  it("distinguishes a genuine zero from a suppressed value", () => {
    expect(formatRate(0)).toBe("0%");
    expect(formatRate(null)).toBeNull();
  });
});

describe("formatDays", () => {
  it("returns null when suppressed", () => {
    expect(formatDays(null)).toBeNull();
  });

  it("drops a trailing zero decimal", () => {
    expect(formatDays(7)).toBe("7일");
    expect(formatDays(7.4)).toBe("7.4일");
    expect(formatDays(7.04)).toBe("7일");
  });
});

describe("canPublishRates", () => {
  it("only allows the two states above the publishable bar", () => {
    expect(canPublishRates("PUBLISHABLE")).toBe(true);
    expect(canPublishRates("HIGH_CONFIDENCE")).toBe(true);
    expect(canPublishRates("EARLY_SIGNAL")).toBe(false);
    expect(canPublishRates("INSUFFICIENT_DATA")).toBe(false);
  });
});

describe("responseVerdict", () => {
  it("withholds a verdict when the sample is too small", () => {
    const verdict = responseVerdict(null, "INSUFFICIENT_DATA");
    expect(verdict.tone).toBe("unknown");
    expect(verdict.label).toBe("판정 보류");
  });

  it("withholds a verdict even if a rate leaks through below the bar", () => {
    // Defence in depth: eligibility governs, not the presence of a number.
    const verdict = responseVerdict(0.1, "EARLY_SIGNAL");
    expect(verdict.tone).toBe("unknown");
  });

  it("gives a strong positive verdict for high response rates", () => {
    const verdict = responseVerdict(0.91, "PUBLISHABLE");
    expect(verdict.label).toBe("답장 생존");
    expect(verdict.tone).toBe("alive");
  });

  it("gives a negative verdict only on a qualified sample", () => {
    const verdict = responseVerdict(0.2, "PUBLISHABLE");
    expect(verdict.label).toBe("멸종위기");
    expect(verdict.tone).toBe("extinct");
  });
});
