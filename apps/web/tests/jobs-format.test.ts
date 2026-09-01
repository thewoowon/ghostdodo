/**
 * Posting presentation rules.
 *
 * The deadline is the part that can be wrong in a way nobody notices: a
 * closing date is a Korean calendar date, and comparing it in the viewer's
 * timezone would close a posting early for anyone west of Seoul.
 */
import { describe, expect, it } from "vitest";

import { jobClosing, jobFacets, seoulToday, sourceName } from "@/lib/format/jobs";

const OPEN = { is_open: true, closes_on: null };

describe("seoulToday", () => {
  it("reads the Seoul date, not the viewer's", () => {
    // 21:00 UTC on the 30th is already the 31st in Seoul (UTC+9).
    expect(seoulToday(new Date("2026-08-30T21:00:00Z"))).toBe("2026-08-31");
  });
});

describe("jobClosing", () => {
  it("labels a posting with no deadline as 상시 채용", () => {
    expect(jobClosing(OPEN, "2026-08-31")).toEqual({
      kind: "always",
      label: "상시 채용",
    });
  });

  it("counts down inside the last week", () => {
    const closing = jobClosing(
      { is_open: true, closes_on: "2026-09-03" },
      "2026-08-31",
    );
    expect(closing).toEqual({ kind: "soon", label: "마감 D-3", days: 3 });
  });

  it("says 오늘 마감 on the closing date itself", () => {
    expect(
      jobClosing({ is_open: true, closes_on: "2026-08-31" }, "2026-08-31").kind,
    ).toBe("today");
  });

  it("shows a plain date when the deadline is far off", () => {
    expect(
      jobClosing({ is_open: true, closes_on: "2026-12-01" }, "2026-08-31"),
    ).toEqual({ kind: "dated", label: "2026-12-01 마감" });
  });

  it("explains a closed posting rather than hiding it", () => {
    // The API owns the open/closed decision; a shared link to an expired
    // posting has to say what happened.
    expect(
      jobClosing({ is_open: false, closes_on: "2026-08-01" }, "2026-08-31"),
    ).toEqual({ kind: "closed", label: "마감된 공고" });
  });

  it("trusts is_open over a future date", () => {
    expect(
      jobClosing({ is_open: false, closes_on: "2027-01-01" }, "2026-08-31").kind,
    ).toBe("closed");
  });
});

describe("sourceName", () => {
  it("prefers the board's own recorded name", () => {
    expect(sourceName({ source: "WANTED", source_label: "원티드" })).toBe("원티드");
  });

  it("falls back to the source enum's label so attribution is never blank", () => {
    expect(sourceName({ source: "SARAMIN", source_label: null })).toBe("사람인");
  });
});

describe("jobFacets", () => {
  it("skips whatever the posting did not record", () => {
    expect(
      jobFacets({
        role_category: "SOFTWARE_ENGINEERING",
        employment_type: null,
        location: "서울 강남구",
      }),
    ).toEqual(["개발", "서울 강남구"]);
  });

  it("returns nothing rather than empty chips", () => {
    expect(
      jobFacets({ role_category: null, employment_type: null, location: null }),
    ).toEqual([]);
  });
});
