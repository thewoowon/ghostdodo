/**
 * Search results under the launch gate (docs/08 §11).
 *
 * A real company is listed so applicants can find it and report on it, but
 * while publication is held back the row says nothing about what has been
 * filed — not even a count.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyResultList } from "@/components/search/CompanyResultList";
import type { CompanySummary } from "@/lib/api/types";

function company(overrides: Partial<CompanySummary>): CompanySummary {
  return {
    id: "c1",
    slug: "hanbit",
    display_name_ko: "한빛제조",
    name_en: null,
    industry: "제조",
    public_report_count: 0,
    is_demo: false,
    published: false,
    ...overrides,
  };
}

describe("CompanyResultList", () => {
  it("lists a held-back company with no report count", () => {
    render(<CompanyResultList companies={[company({})]} query="한빛" />);

    expect(screen.getByRole("link", { name: /한빛제조/ })).toHaveAttribute(
      "href",
      "/companies/hanbit",
    );
    expect(screen.queryByText(/기록 \d+건/)).not.toBeInTheDocument();
  });

  it("shows the count for a published company", () => {
    render(
      <CompanyResultList
        companies={[company({ is_demo: true, published: true, public_report_count: 34 })]}
        query="한빛"
      />,
    );

    expect(screen.getByText("기록 34건")).toBeInTheDocument();
  });
});
