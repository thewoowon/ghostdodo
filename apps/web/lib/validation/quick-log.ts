/**
 * Quick log validation.
 *
 * Mirrors `QuickLogInput` in `apps/api/app/modules/reports/schemas.py`. The
 * server stays authoritative; this catches the same mistakes before thirty
 * lines make a round trip.
 */
import type {
  ApplicationSource,
  EmploymentType,
  HiringStage,
  Outcome,
  RoleCategory,
} from "@/lib/domain";

export const QUICK_LOG_MAX_ITEMS = 30;

export type QuickLogDefaults = {
  role_title: string;
  role_category: RoleCategory;
  employment_type: EmploymentType;
  source: ApplicationSource;
};

export type QuickLogRow = {
  key: string;
  company_id: string;
  company_name: string;
  application_date: string;
  furthest_stage: HiringStage;
  last_contact: string;
  result_received: boolean;
  result_date: string;
  /** Empty until chosen: a received result is never assumed to be a
   *  rejection, or anything else. */
  outcome: Exclude<Outcome, "UNKNOWN"> | "";
};

export type QuickLogErrors = {
  defaults: Partial<Record<keyof QuickLogDefaults, string>>;
  rows: Record<string, Partial<Record<keyof QuickLogRow, string>>>;
};

export function blankRow(key: string): QuickLogRow {
  return {
    key,
    company_id: "",
    company_name: "",
    application_date: "",
    furthest_stage: "APPLICATION",
    last_contact: "",
    result_received: false,
    result_date: "",
    outcome: "",
  };
}

export function validateQuickLog(
  defaults: QuickLogDefaults,
  rows: QuickLogRow[],
  today: string = new Date().toISOString().slice(0, 10),
): QuickLogErrors {
  const errors: QuickLogErrors = { defaults: {}, rows: {} };
  const title = defaults.role_title.trim();
  if (!title) errors.defaults.role_title = "지원한 직무를 입력해 주세요.";
  else if (title.length > 120) errors.defaults.role_title = "120자 이내로 입력해 주세요.";

  for (const row of rows) {
    const e: Partial<Record<keyof QuickLogRow, string>> = {};
    if (!row.company_id) e.company_id = "회사를 선택해 주세요.";
    if (!row.application_date) e.application_date = "지원일을 입력해 주세요.";
    else if (row.application_date > today) e.application_date = "미래 날짜는 입력할 수 없습니다.";
    // Without it the silence clock starts at the application, and weeks the
    // company was in touch would count as silence.
    if (row.furthest_stage !== "APPLICATION" && !row.last_contact) {
      e.last_contact = "마지막으로 연락받은 날짜가 필요합니다.";
    }
    if (row.result_received) {
      if (!row.result_date) e.result_date = "결과를 받은 날짜를 입력해 주세요.";
      else if (row.application_date && row.result_date < row.application_date) {
        e.result_date = "지원일보다 앞설 수 없습니다.";
      }
      if (!row.outcome) e.outcome = "결과를 골라 주세요.";
    }
    if (Object.keys(e).length > 0) errors.rows[row.key] = e;
  }
  return errors;
}

export function hasErrors(errors: QuickLogErrors): boolean {
  return Object.keys(errors.defaults).length > 0 || Object.keys(errors.rows).length > 0;
}

const asDate = (date: string) => date || null;

export function toQuickLogInput(defaults: QuickLogDefaults, rows: QuickLogRow[]) {
  return {
    defaults: { ...defaults, role_title: defaults.role_title.trim() },
    items: rows.map((row) => ({
      company_id: row.company_id,
      application_date: row.application_date,
      furthest_stage: row.furthest_stage,
      last_company_interaction_on:
        row.furthest_stage === "APPLICATION" ? asDate(row.last_contact) : row.last_contact,
      result_received: row.result_received,
      result_received_on: row.result_received ? row.result_date : null,
      outcome: row.result_received && row.outcome ? row.outcome : "UNKNOWN",
    })),
  };
}
