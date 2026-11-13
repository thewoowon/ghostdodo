/**
 * Asking for a company the directory does not have.
 *
 * Three places used to promise "등록을 요청할 수 있습니다" with nothing to
 * press. What matters now: the request carries the name the visitor was
 * searching for, a company that already exists is linked rather than
 * queued, and a rate limit reads as plain Korean.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CompanyRequestForm } from "@/components/company/CompanyRequestForm";

function mockResponse(status: number, body: unknown) {
  const calls: RequestInit[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init) calls.push(init);
      return new Response(JSON.stringify(body), { status });
    }),
  );
  return calls;
}

async function openAndSubmit() {
  await userEvent.click(screen.getByRole("button", { name: "회사 등록 요청하기" }));
  await userEvent.click(screen.getByRole("button", { name: "요청 보내기" }));
}

describe("CompanyRequestForm", () => {
  it("sends the name the visitor searched for and confirms it is queued", async () => {
    const calls = mockResponse(202, {
      id: "r1",
      status: "PENDING",
      message: "",
      existing_slug: null,
    });
    render(<CompanyRequestForm initialName="작은스타트업" />);

    await openAndSubmit();

    expect(await screen.findByRole("status")).toHaveTextContent("등록 요청이 접수되었습니다");
    expect(JSON.parse(String(calls[0]?.body))).toEqual({
      name: "작은스타트업",
      website: null,
      note: null,
    });
  });

  it("links to a company that already exists instead of queueing", async () => {
    mockResponse(202, {
      id: null,
      status: "EXISTS",
      message: "이미 도감에 있는 회사입니다.",
      existing_slug: "비바리퍼블리카",
    });
    render(<CompanyRequestForm initialName="토스" />);

    await openAndSubmit();

    expect(await screen.findByRole("link", { name: "회사 페이지로 가기" })).toHaveAttribute(
      "href",
      "/companies/비바리퍼블리카",
    );
  });

  it("explains a rate limit in plain Korean", async () => {
    mockResponse(429, {
      error: { code: "RATE_LIMITED", message: "x", request_id: "r", details: {} },
    });
    render(<CompanyRequestForm initialName="작은스타트업" />);

    await openAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent("등록 요청이 너무 잦습니다");
  });
});
