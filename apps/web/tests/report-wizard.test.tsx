/**
 * Report wizard critical path (required by docs/10 quality bar).
 *
 * Covers the flow a real contributor walks: pick a company, fill the hiring
 * context, choose a stage, describe the timeline, confirm what becomes
 * public, and submit — plus the guards that stop them from advancing on
 * incomplete or unsafe input.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReportWizard } from "@/components/report/ReportWizard";

const COMPANY = {
  id: "11111111-1111-4111-8111-111111111111",
  slug: "dodolab",
  display_name_ko: "도도랩",
  name_en: "DodoLab",
  industry: "소프트웨어",
  public_report_count: 34,
  is_demo: true,
};

/** Requests the wizard made, so assertions can inspect the real payload. */
let calls: { url: string; init: RequestInit | undefined }[] = [];

function mockFetch(overrides: { submitStatus?: number } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      const href = String(url);
      calls.push({ url: href, init });

      if (href.includes("/companies/search")) {
        return new Response(JSON.stringify([COMPANY]), { status: 200 });
      }
      if (href.endsWith("/reports")) {
        return new Response(
          JSON.stringify({ id: "report-1", verification_status: "DRAFT" }),
          { status: 201 },
        );
      }
      if (href.includes("/submit")) {
        const status = overrides.submitStatus ?? 200;
        if (status !== 200) {
          return new Response(
            JSON.stringify({
              error: {
                code: "DUPLICATE_REPORT",
                message: "동일한 채용 과정에 대한 기록이 이미 있습니다.",
                request_id: "req-1",
                details: {},
              },
            }),
            { status },
          );
        }
        return new Response(
          JSON.stringify({ id: "report-1", verification_status: "NEEDS_REVIEW" }),
          { status: 200 },
        );
      }
      return new Response("{}", { status: 200 });
    }),
  );
}

async function pickCompany(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("회사 검색"), "도도랩");
  const option = await screen.findByRole("button", { name: /도도랩/ });
  await user.click(option);
}

async function next(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "다음" }));
}

describe("ReportWizard", () => {
  beforeEach(() => {
    calls = [];
    mockFetch();
  });

  it("blocks advancing past the company step until one is selected", async () => {
    const user = userEvent.setup();
    render(<ReportWizard />);

    await next(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("회사를 선택해 주세요");
  });

  it("blocks advancing without a job title or application date", async () => {
    const user = userEvent.setup();
    render(<ReportWizard />);

    await pickCompany(user);
    await next(user);

    // Now on the hiring-context step with both required fields empty; the
    // step reports every problem at once rather than one at a time.
    await next(user);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((a) => a.textContent)).toEqual(
      expect.arrayContaining([
        "지원한 직무를 입력해 주세요.",
        "날짜 형식이 올바르지 않습니다.",
      ]),
    );
  });

  it("requires a promised date once the user says a date was promised", async () => {
    const user = userEvent.setup();
    render(<ReportWizard />);

    await pickCompany(user);
    await next(user);

    await user.type(screen.getByRole("textbox"), "프론트엔드 개발자");
    await user.type(screen.getByLabelText(/지원한 날짜/), "2026-06-01");
    await next(user); // -> stage
    await next(user); // -> timeline

    const promisedGroup = screen.getByRole("group", {
      name: "회사가 결과 안내 예정일을 알려줬나요?",
    });
    await user.click(within(promisedGroup).getByRole("button", { name: "예" }));

    await next(user);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "결과 안내 예정일을 입력해 주세요",
    );
  });

  it("warns before submitting text that names an individual", async () => {
    const user = userEvent.setup();
    render(<ReportWizard />);

    await pickCompany(user);
    await next(user);
    await user.type(screen.getByRole("textbox"), "백엔드 개발자");
    await user.type(screen.getByLabelText(/지원한 날짜/), "2026-06-01");
    await next(user); // stage
    await next(user); // timeline
    await next(user); // outcome

    await user.type(
      screen.getByRole("textbox", { name: /추가 설명/ }),
      "김철수 팀장이 연락을 안 줬어요",
    );

    const warning = await screen.findByRole("alert");
    expect(warning).toHaveTextContent("개인을 특정하는 표현은 기록할 수 없습니다");
  });

  it("completes the happy path and submits a structured report", async () => {
    const user = userEvent.setup();
    render(<ReportWizard />);

    await pickCompany(user);
    await next(user);

    await user.type(screen.getByRole("textbox"), "프론트엔드 개발자");
    await user.type(screen.getByLabelText(/지원한 날짜/), "2026-06-01");
    await next(user);

    await user.click(screen.getByRole("radio", { name: "1차 면접" }));
    await next(user);

    await user.type(
      screen.getByLabelText(/회사와 마지막으로 연락한 날/),
      "2026-06-20",
    );
    await next(user);

    await user.click(screen.getByRole("radio", { name: "결과 미수신" }));
    await next(user);

    // The preview must state plainly what stays private.
    expect(screen.getByText("공개되는 내용")).toBeInTheDocument();
    expect(screen.getByText("공개되지 않는 내용")).toBeInTheDocument();
    expect(
      screen.getByText(/작성자 계정 정보 — 회사에도, 다른 이용자에게도 공개되지 않습니다/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "기록 제출하기" }));

    expect(await screen.findByText("기록이 접수되었습니다")).toBeInTheDocument();

    const createCall = calls.find((c) => c.url.endsWith("/reports"));
    expect(createCall).toBeDefined();
    const payload = JSON.parse(String(createCall!.init?.body));
    expect(payload).toMatchObject({
      company_id: COMPANY.id,
      role_title: "프론트엔드 개발자",
      furthest_stage: "INTERVIEW_1",
      application_date: "2026-06-01",
      result_received: false,
      outcome: "UNKNOWN",
    });
    // Idempotency key must ride along so a retry cannot double-post.
    expect(
      (createCall!.init?.headers as Record<string, string>)["X-Idempotency-Key"],
    ).toBeTruthy();

    expect(calls.some((c) => c.url.includes("/submit"))).toBe(true);
  });

  it("surfaces a duplicate-report error without losing the draft", async () => {
    mockFetch({ submitStatus: 409 });
    const user = userEvent.setup();
    render(<ReportWizard />);

    await pickCompany(user);
    await next(user);
    await user.type(screen.getByRole("textbox"), "데이터 분석가");
    await user.type(screen.getByLabelText(/지원한 날짜/), "2026-05-01");
    await next(user);
    await next(user);
    await next(user);
    await next(user);

    await user.click(screen.getByRole("button", { name: "기록 제출하기" }));

    await waitFor(() => {
      expect(
        screen.getByText("동일한 채용 과정에 대한 기록이 이미 있습니다."),
      ).toBeInTheDocument();
    });
    // Still on the review step so the draft can be corrected and retried.
    // The job title itself is intentionally absent from the preview: it stays
    // private and is published only as a role category.
    expect(screen.getByText("공개되는 내용")).toBeInTheDocument();
    expect(screen.queryByText("데이터 분석가")).not.toBeInTheDocument();
  });

  it("restores an interrupted draft from local storage", async () => {
    window.localStorage.setItem(
      "ghostdodo.report.draft.v1",
      JSON.stringify({ company_id: COMPANY.id, company_name: "도도랩", role_title: "PM" }),
    );

    render(<ReportWizard />);

    expect(
      await screen.findByText("작성 중이던 내용을 불러왔습니다."),
    ).toBeInTheDocument();
  });
});
