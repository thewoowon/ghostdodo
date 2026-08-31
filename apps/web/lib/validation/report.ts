/**
 * Report wizard validation.
 *
 * Mirrors the Pydantic constraints in `apps/api/app/modules/reports/schemas.py`
 * so the client catches the same mistakes the server would (docs/04 §7). The
 * server remains authoritative; this exists to avoid a round trip, not to
 * replace the check.
 */
import { z } from "zod";

import {
  APPLICATION_SOURCES,
  CHANNELS,
  EMPLOYMENT_TYPES,
  HIRING_STAGES,
  OUTCOMES,
  ROLE_CATEGORIES,
} from "@/lib/domain";

export const FREE_CONTEXT_MAX = 500;

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "날짜 형식이 올바르지 않습니다.");

export const companyStepSchema = z.object({
  company_id: z.string().uuid("회사를 선택해 주세요."),
  company_name: z.string().min(1, "회사를 선택해 주세요."),
});

export const contextStepSchema = z.object({
  role_title: z
    .string()
    .trim()
    .min(1, "지원한 직무를 입력해 주세요.")
    .max(120, "120자 이내로 입력해 주세요."),
  role_category: z.enum(ROLE_CATEGORIES),
  employment_type: z.enum(EMPLOYMENT_TYPES),
  source: z.enum(APPLICATION_SOURCES),
  application_date: isoDate,
});

export const stageStepSchema = z.object({
  furthest_stage: z.enum(HIRING_STAGES),
});

export const timelineStepSchema = z
  .object({
    last_company_interaction_at: isoDate.or(z.literal("")),
    promised_result: z.boolean(),
    promised_result_date: isoDate.or(z.literal("")),
    result_received: z.boolean(),
    result_received_at: isoDate.or(z.literal("")),
    result_channel: z.enum(CHANNELS).or(z.literal("")),
  })
  .superRefine((value, ctx) => {
    if (value.promised_result && !value.promised_result_date) {
      ctx.addIssue({
        code: "custom",
        path: ["promised_result_date"],
        message: "결과 안내 예정일을 입력해 주세요.",
      });
    }
    if (value.result_received && !value.result_received_at) {
      ctx.addIssue({
        code: "custom",
        path: ["result_received_at"],
        message: "결과를 받은 날짜를 입력해 주세요.",
      });
    }
  });

export const outcomeStepSchema = z.object({
  outcome: z.enum(OUTCOMES),
  free_context: z
    .string()
    .max(FREE_CONTEXT_MAX, `${FREE_CONTEXT_MAX}자 이내로 입력해 주세요.`)
    .optional(),
});

export type WizardDraft = {
  company_id: string;
  company_name: string;
  role_title: string;
  role_category: (typeof ROLE_CATEGORIES)[number];
  employment_type: (typeof EMPLOYMENT_TYPES)[number];
  source: (typeof APPLICATION_SOURCES)[number];
  application_date: string;
  furthest_stage: (typeof HIRING_STAGES)[number];
  last_company_interaction_at: string;
  promised_result: boolean;
  promised_result_date: string;
  result_received: boolean;
  result_received_at: string;
  result_channel: (typeof CHANNELS)[number] | "";
  outcome: (typeof OUTCOMES)[number];
  free_context: string;
};

export const EMPTY_DRAFT: WizardDraft = {
  company_id: "",
  company_name: "",
  role_title: "",
  role_category: "SOFTWARE_ENGINEERING",
  employment_type: "FULL_TIME",
  source: "COMPANY_SITE",
  application_date: "",
  furthest_stage: "APPLICATION",
  last_company_interaction_at: "",
  promised_result: false,
  promised_result_date: "",
  result_received: false,
  result_received_at: "",
  result_channel: "",
  outcome: "UNKNOWN",
  free_context: "",
};

/**
 * Heuristics that warn a contributor before they publish something they
 * cannot take back. Advisory only — the server enforces the real policy.
 */
export function detectPossiblePii(text: string): string[] {
  const warnings: string[] = [];
  if (/[\w.+-]+@[\w-]+\.[\w.]+/.test(text)) {
    warnings.push("이메일 주소로 보이는 내용이 있습니다.");
  }
  if (/01[016-9][-\s]?\d{3,4}[-\s]?\d{4}/.test(text)) {
    warnings.push("전화번호로 보이는 내용이 있습니다.");
  }
  if (/[가-힣]{2,4}\s*(님|씨|과장|부장|팀장|이사|대표|면접관)/.test(text)) {
    warnings.push(
      "개인의 이름이나 직함으로 보이는 내용이 있습니다. 개인을 특정하는 표현은 기록할 수 없습니다.",
    );
  }
  return warnings;
}

/** Maps the wizard's form shape onto the API's report payload. */
export function toReportInput(draft: WizardDraft) {
  const asDateTime = (date: string) => (date ? `${date}T00:00:00Z` : null);
  return {
    company_id: draft.company_id,
    role_title: draft.role_title.trim(),
    role_category: draft.role_category,
    employment_type: draft.employment_type,
    source: draft.source,
    application_date: draft.application_date,
    furthest_stage: draft.furthest_stage,
    last_company_interaction_at: asDateTime(draft.last_company_interaction_at),
    promised_result: draft.promised_result,
    promised_result_date: draft.promised_result_date || null,
    result_received: draft.result_received,
    result_received_at: asDateTime(draft.result_received_at),
    result_channel: draft.result_channel || null,
    outcome: draft.outcome,
    context_tags: [],
    free_context: draft.free_context.trim() || null,
  };
}
