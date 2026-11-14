/**
 * Header navigation.
 *
 * On phones the inline row overflowed the viewport and the browser zoomed
 * every page out, so the links moved into a disclosure panel. What matters:
 * the toggle reports its state, Escape and navigation close it, and the
 * session is still asked for once even though it is rendered in two places.
 *
 * Which of the two layouts shows is CSS, which jsdom does not apply — both
 * are in the DOM here, so queries are scoped to the panel.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/companies/dodolab";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteNav } from "@/components/layout/SiteNav";

let sessionCalls = 0;

function mockSession(user: { handle: string } | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      if (String(url).includes("/auth/me")) {
        sessionCalls += 1;
        return user
          ? new Response(JSON.stringify({ id: "u1", handle: user.handle, rank: "OBSERVER" }), {
              status: 200,
            })
          : new Response(
              JSON.stringify({
                error: { code: "UNAUTHENTICATED", message: "", request_id: "r", details: {} },
              }),
              { status: 401 },
            );
      }
      return new Response("{}", { status: 200 });
    }),
  );
}

function panel() {
  const toggle = screen.getByRole("button", { name: /메뉴/ });
  const id = toggle.getAttribute("aria-controls");
  return { toggle, panel: document.getElementById(id!)! };
}

beforeEach(() => {
  pathname = "/companies/dodolab";
  sessionCalls = 0;
});

describe("SiteNav", () => {
  it("starts closed and opens on the toggle", async () => {
    mockSession(null);
    render(<SiteNav />);
    const { toggle, panel: p } = panel();

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(p).not.toBeVisible();

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveAccessibleName("메뉴 닫기");
    expect(p).toBeVisible();
    expect(within(p).getByRole("link", { name: "측정 기준" })).toHaveAttribute(
      "href",
      "/methodology",
    );
  });

  it("leaves 채용공고 out while jobs are closed, and shows it once opened", async () => {
    // Production closed jobs: the only postings were demo fixtures, which
    // read as real next to real companies.
    mockSession(null);
    vi.stubEnv("NEXT_PUBLIC_ENABLE_JOBS", "");
    const { unmount } = render(<SiteNav />);
    expect(screen.queryByRole("link", { name: "채용공고" })).not.toBeInTheDocument();
    unmount();

    vi.stubEnv("NEXT_PUBLIC_ENABLE_JOBS", "true");
    render(<SiteNav />);
    expect(screen.getAllByRole("link", { name: "채용공고" })[0]).toHaveAttribute("href", "/jobs");
    vi.unstubAllEnvs();
  });

  it("closes on Escape and hands focus back to the toggle", async () => {
    mockSession(null);
    render(<SiteNav />);
    const { toggle, panel: p } = panel();

    await userEvent.click(toggle);
    await userEvent.keyboard("{Escape}");

    expect(p).not.toBeVisible();
    expect(toggle).toHaveFocus();
  });

  it("closes when the route changes", async () => {
    mockSession(null);
    const { rerender } = render(<SiteNav />);
    const { toggle, panel: p } = panel();

    await userEvent.click(toggle);
    pathname = "/jobs";
    rerender(<SiteNav />);

    expect(p).not.toBeVisible();
  });

  it("keeps 기록하기 outside the panel, always reachable", () => {
    mockSession(null);
    render(<SiteNav />);
    const { panel: p } = panel();

    const cta = screen.getByRole("link", { name: "기록하기" });
    expect(cta).toHaveAttribute("href", "/report/new");
    expect(p).not.toContainElement(cta);
  });

  it("offers sign-in in the panel, returning to the current page", async () => {
    mockSession(null);
    render(<SiteNav />);
    const { toggle, panel: p } = panel();
    await userEvent.click(toggle);

    const signIn = await within(p).findByRole("link", { name: "로그인" });
    expect(signIn).toHaveAttribute("href", "/sign-in?next=%2Fcompanies%2Fdodolab");
  });

  it("asks for the session once, and shows the account in the panel", async () => {
    mockSession({ handle: "관찰자01" });
    render(<SiteNav />);
    const { toggle, panel: p } = panel();
    await userEvent.click(toggle);

    const me = await within(p).findByRole("link", { name: /내 활동/ });
    expect(me).toHaveAttribute("href", "/me");
    expect(me).toHaveTextContent("관찰자01");
    expect(within(p).getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
    await waitFor(() => expect(sessionCalls).toBe(1));
  });
});

describe("SiteHeader", () => {
  // The other half of the wordmark's contract (tests/wordmark.test.tsx):
  // the mark is hidden, so the home link has to carry the brand name.
  it("names the home link, since the wordmark is hidden", () => {
    mockSession(null);
    render(<SiteHeader />);

    expect(screen.getByRole("link", { name: "GhostDodo 홈" })).toHaveAttribute("href", "/");
  });
});
