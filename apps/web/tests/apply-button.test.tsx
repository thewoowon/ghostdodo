/**
 * The outbound apply deep link.
 *
 * The rule this file exists to hold: recording a click must never be able to
 * stop someone from applying. The anchor is real, it points at the employer,
 * and the accounting call rides alongside the navigation rather than in
 * front of it.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApplyButton } from "@/components/jobs/ApplyButton";

const JOB_ID = "11111111-1111-4111-8111-111111111111";
const APPLY_URL = "https://example.com/dodolab/jobs/1";

let calls: { url: string; init: RequestInit | undefined }[] = [];

function mockFetch(behaviour: "ok" | "error" = "ok") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      if (behaviour === "error") throw new TypeError("network down");
      return new Response(
        JSON.stringify({ apply_url: APPLY_URL, recorded: true }),
        { status: 200 },
      );
    }),
  );
}

beforeEach(() => {
  calls = [];
});

describe("ApplyButton", () => {
  it("links straight to the posting in a new tab", () => {
    mockFetch();
    render(<ApplyButton jobId={JOB_ID} applyUrl={APPLY_URL} isOpen />);

    const link = screen.getByRole("link", { name: /지원하러 가기/ });
    expect(link).toHaveAttribute("href", APPLY_URL);
    expect(link).toHaveAttribute("target", "_blank");
    // noreferrer keeps the referring path out of the employer's analytics.
    expect(link.getAttribute("rel")).toContain("noreferrer");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("records the click without preventing the navigation", async () => {
    mockFetch();
    render(<ApplyButton jobId={JOB_ID} applyUrl={APPLY_URL} isOpen />);

    const link = screen.getByRole("link", { name: /지원하러 가기/ });
    const clicked = await userEvent.click(link).then(() => true);
    expect(clicked).toBe(true);

    expect(calls).toHaveLength(1);
    const call = calls[0]!;
    expect(call.url).toContain(`/jobs/${JOB_ID}/outbound-click`);
    expect(call.init?.method).toBe("POST");
    // The request must survive the navigation it accompanies.
    expect(call.init?.keepalive).toBe(true);
    expect(JSON.parse(String(call.init?.body))).toEqual({
      referrer_path: window.location.pathname,
    });
  });

  it("stays a working link when the accounting call fails", async () => {
    mockFetch("error");
    render(<ApplyButton jobId={JOB_ID} applyUrl={APPLY_URL} isOpen />);

    const link = screen.getByRole("link", { name: /지원하러 가기/ });
    await userEvent.click(link);

    // No throw, no error surface, href untouched — the user is on their way.
    expect(link).toHaveAttribute("href", APPLY_URL);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("offers no link on a closed posting", () => {
    mockFetch();
    render(<ApplyButton jobId={JOB_ID} applyUrl={APPLY_URL} isOpen={false} />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("마감된 공고")).toBeInTheDocument();
  });

  it("offers no link when the API suppressed the URL", () => {
    // `apply_url` is null when the stored URL is not a linkable http(s)
    // address — a dead or unsafe link must never reach an href.
    mockFetch();
    render(<ApplyButton jobId={JOB_ID} applyUrl={null} isOpen />);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("지원 링크 확인 중")).toBeInTheDocument();
  });
});
