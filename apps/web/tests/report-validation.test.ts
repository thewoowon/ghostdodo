import { describe, expect, it } from "vitest";

import {
  EMPTY_DRAFT,
  detectPossiblePii,
  timelineStepSchema,
  toReportInput,
} from "@/lib/validation/report";

describe("timeline validation", () => {
  it("requires a date when the company promised one", () => {
    const result = timelineStepSchema.safeParse({
      ...EMPTY_DRAFT,
      promised_result: true,
      promised_result_date: "",
    });
    expect(result.success).toBe(false);
  });

  it("requires a date when a result was received", () => {
    const result = timelineStepSchema.safeParse({
      ...EMPTY_DRAFT,
      result_received: true,
      result_received_at: "",
    });
    expect(result.success).toBe(false);
  });

  it("accepts a complete timeline", () => {
    const result = timelineStepSchema.safeParse({
      ...EMPTY_DRAFT,
      last_company_interaction_at: "2026-07-01",
      promised_result: true,
      promised_result_date: "2026-07-15",
      result_received: true,
      result_received_at: "2026-07-20",
      result_channel: "EMAIL",
    });
    expect(result.success).toBe(true);
  });
});

describe("PII heuristics", () => {
  it("flags an email address", () => {
    expect(detectPossiblePii("연락처는 hr@example.com 입니다")).toHaveLength(1);
  });

  it("flags a Korean mobile number", () => {
    expect(detectPossiblePii("010-1234-5678로 연락 옴")).toHaveLength(1);
  });

  it("flags a named individual with a title", () => {
    // Naming recruiters or interviewers is prohibited (docs/07 §6).
    expect(detectPossiblePii("김철수 팀장이 면접을 봤습니다").length).toBeGreaterThan(0);
  });

  it("does not flag ordinary factual context", () => {
    expect(
      detectPossiblePii("결과 안내 예정일 이후 별도 안내를 받지 못했습니다"),
    ).toHaveLength(0);
  });
});

describe("toReportInput", () => {
  it("sends null rather than empty strings for optional dates", () => {
    const payload = toReportInput({
      ...EMPTY_DRAFT,
      company_id: "11111111-1111-4111-8111-111111111111",
      role_title: "  프론트엔드 개발자  ",
      application_date: "2026-06-01",
    });
    expect(payload.promised_result_date).toBeNull();
    expect(payload.result_received_at).toBeNull();
    expect(payload.result_channel).toBeNull();
    expect(payload.free_context).toBeNull();
    // Trimmed, so stray whitespace never reaches the record.
    expect(payload.role_title).toBe("프론트엔드 개발자");
  });

  it("converts date-only fields to UTC timestamps", () => {
    const payload = toReportInput({
      ...EMPTY_DRAFT,
      application_date: "2026-06-01",
      last_company_interaction_at: "2026-06-20",
    });
    expect(payload.last_company_interaction_at).toBe("2026-06-20T00:00:00Z");
    // application_date stays a plain date — the API stores it as DATE.
    expect(payload.application_date).toBe("2026-06-01");
  });
});
