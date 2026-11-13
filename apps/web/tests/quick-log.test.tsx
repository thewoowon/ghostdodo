/**
 * The quick log, client side.
 *
 * Mirrors the API's rules so thirty lines are not sent to be bounced: a
 * line past the application needs its last contact (or the silence clock
 * would start at the application and count weeks the company was in
 * touch), and a received result is never assumed to be anything — the
 * outcome must be chosen.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

import { QuickLog } from "@/components/report/QuickLog";
import {
  blankRow,
  hasErrors,
  toQuickLogInput,
  validateQuickLog,
  type QuickLogDefaults,
} from "@/lib/validation/quick-log";

const DEFAULTS: QuickLogDefaults = {
  role_title: "백엔드 개발자",
  role_category: "SOFTWARE_ENGINEERING",
  employment_type: "FULL_TIME",
  source: "WANTED",
};

function row(overrides: Partial<ReturnType<typeof blankRow>> = {}) {
  return {
    ...blankRow("r1"),
    company_id: "c1",
    company_name: "카카오",
    application_date: "2026-09-01",
    ...overrides,
  };
}

describe("validateQuickLog", () => {
  it("accepts an application-stage line with no contact date", () => {
    expect(hasErrors(validateQuickLog(DEFAULTS, [row()], "2026-11-13"))).toBe(false);
  });

  it("asks for the last contact once past the application", () => {
    const errors = validateQuickLog(DEFAULTS, [row({ furthest_stage: "INTERVIEW_1" })], "2026-11-13");
    expect(errors.rows.r1?.last_contact).toBeTruthy();
  });

  it("never assumes what a received result was", () => {
    const errors = validateQuickLog(
      DEFAULTS,
      [row({ result_received: true, result_date: "2026-09-20" })],
      "2026-11-13",
    );
    expect(errors.rows.r1?.outcome).toBeTruthy();
  });

  it("rejects a result dated before the application", () => {
    const errors = validateQuickLog(
      DEFAULTS,
      [row({ result_received: true, result_date: "2026-08-01", outcome: "REJECTED" })],
      "2026-11-13",
    );
    expect(errors.rows.r1?.result_date).toBeTruthy();
  });

  it("needs a role and a chosen company", () => {
    const errors = validateQuickLog(
      { ...DEFAULTS, role_title: "  " },
      [row({ company_id: "" })],
      "2026-11-13",
    );
    expect(errors.defaults.role_title).toBeTruthy();
    expect(errors.rows.r1?.company_id).toBeTruthy();
  });
});

describe("toQuickLogInput", () => {
  it("sends UNKNOWN only when no result came, and no stray dates", () => {
    const body = toQuickLogInput(DEFAULTS, [
      row({ result_date: "2026-09-20", outcome: "PASSED" }),
    ]);
    expect(body.items[0]).toEqual({
      company_id: "c1",
      application_date: "2026-09-01",
      furthest_stage: "APPLICATION",
      last_company_interaction_on: null,
      result_received: false,
      result_received_on: null,
      outcome: "UNKNOWN",
    });
  });
});

describe("QuickLog", () => {
  it("holds the submit until the required fields are filled", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<QuickLog />);

    await userEvent.click(screen.getByRole("button", { name: "1곳 기록하기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("확인이 필요한 칸");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("adds and removes company lines", async () => {
    render(<QuickLog />);
    await userEvent.click(screen.getByRole("button", { name: "+ 회사 추가" }));
    expect(screen.getByRole("button", { name: "2곳 기록하기" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "2번째 회사 지우기" }));
    expect(screen.getByRole("button", { name: "1곳 기록하기" })).toBeInTheDocument();
  });
});
