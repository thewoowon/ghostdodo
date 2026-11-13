/**
 * Company autocomplete on the search page.
 *
 * `/search?q=…` renders its own result list on the server. The box used to
 * search again for that same query on mount and open a dropdown of the same
 * companies over the list, hiding it. Suggestions are for what the visitor
 * types next, not for the query the page already answered.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

import { CompanySearch } from "@/components/search/CompanySearch";

let searches = 0;

beforeEach(() => {
  searches = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      searches += 1;
      return new Response(
        JSON.stringify([
          {
            id: "c1",
            slug: "dodolab",
            display_name_ko: "도도랩",
            name_en: "DodoLab",
            industry: "소프트웨어",
            public_report_count: 34,
            is_demo: true,
          },
        ]),
        { status: 200 },
      );
    }),
  );
});

describe("CompanySearch", () => {
  it("does not search again for the query the page opened with", async () => {
    render(<CompanySearch size="compact" initialQuery="도도" />);

    // Longer than the debounce, so a search would have fired by now.
    await new Promise((resolve) => setTimeout(resolve, 300));

    expect(searches).toBe(0);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("suggests once the visitor types", async () => {
    render(<CompanySearch size="compact" initialQuery="도도" />);

    await userEvent.type(screen.getByRole("combobox"), "랩");

    expect(await screen.findByRole("listbox")).toBeInTheDocument();
    expect(searches).toBeGreaterThan(0);
  });
});
