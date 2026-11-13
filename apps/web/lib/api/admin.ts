/** Moderator-facing API calls. Every one of these requires a session with a
 *  MODERATOR or ADMIN role; the server enforces it. */
import { apiRequest } from "./client";
import type { CompanySummary, PublicReportCard } from "./types";

export type QueueItem = PublicReportCard & {
  company_id: string;
  submitted_at: string | null;
  auto_check_flags: Record<string, unknown>;
  evidence_count: number;
  /** Set when the report came in through the quick log, shared by every
   *  line filed together. */
  batch_id: string | null;
};

export type DisputeItem = {
  id: string;
  company_id: string;
  experience_id: string | null;
  contact_email: string | null;
  claim_summary: string;
  disputed_fields: string[];
  supporting_note: string | null;
  status: string;
  outcome: string | null;
  created_at: string;
  decided_at: string | null;
};

export type ModeratorEvidence = {
  id: string;
  kind: string;
  content_type: string;
  size_bytes: number | null;
  original_filename: string | null;
  review_state: string;
  access_state: string;
  created_at: string;
  signed_url: string;
  signed_url_expires_in_seconds: number;
};

export const REVIEW_DECISIONS = [
  "VERIFY",
  "PARTIALLY_VERIFY",
  "REJECT",
  "REQUEST_REDACTION",
  "MARK_DISPUTED",
  "REMOVE",
] as const;
export type ReviewDecision = (typeof REVIEW_DECISIONS)[number];

export const DECISION_LABELS: Record<ReviewDecision, string> = {
  VERIFY: "검증",
  PARTIALLY_VERIFY: "부분 검증",
  REJECT: "반려",
  REQUEST_REDACTION: "일부 삭제 요청",
  MARK_DISPUTED: "이의 표시",
  REMOVE: "삭제",
};

export const CORRECTION_OUTCOMES = [
  "UPHELD",
  "CORRECTED",
  "RELABELED",
  "REMOVED",
  "REJECTED",
] as const;
export type CorrectionOutcome = (typeof CORRECTION_OUTCOMES)[number];

export const OUTCOME_LABELS: Record<CorrectionOutcome, string> = {
  UPHELD: "기록 유지",
  CORRECTED: "기록 수정",
  RELABELED: "재분류",
  REMOVED: "기록 삭제",
  REJECTED: "요청 기각",
};

export const AUTO_CHECK_LABELS: Record<string, string> = {
  impossible_application_date: "지원일이 미래",
  future_result_date: "결과 수신일이 미래",
  interaction_before_application: "연락일이 지원일보다 빠름",
  promise_before_application: "예정일이 지원일보다 빠름",
  possible_pii: "개인정보 의심 표현",
  very_old_application: "3년 이상 지난 지원",
};

export function fetchQueue(cookie?: string): Promise<QueueItem[]> {
  return apiRequest<QueueItem[]>("/admin/reports", {
    cache: "no-store",
    ...(cookie ? { cookie } : {}),
  });
}

export function fetchDisputes(cookie?: string): Promise<DisputeItem[]> {
  return apiRequest<DisputeItem[]>("/admin/disputes", {
    cache: "no-store",
    ...(cookie ? { cookie } : {}),
  });
}

export function decideReport(
  reportId: string,
  body: { decision: ReviewDecision; reasons?: string[]; note?: string },
) {
  return apiRequest<{ id: string; verification_status: string }>(
    `/admin/reports/${reportId}/decision`,
    { method: "POST", body },
  );
}

export function decideDispute(
  requestId: string,
  body: {
    outcome: CorrectionOutcome;
    decision_note?: string;
    field_corrections?: Record<string, string | boolean | null>;
  },
) {
  return apiRequest<{ id: string; status: string; outcome: string }>(
    `/admin/disputes/${requestId}/decision`,
    { method: "POST", body },
  );
}

/** Requesting this mints a short-lived signed URL AND writes an access log
 *  entry server-side. Never call it speculatively — only when a moderator
 *  has actually asked to view the file. */
export function viewEvidence(evidenceId: string) {
  return apiRequest<ModeratorEvidence>(`/admin/evidence/${evidenceId}`);
}

export type CompanyRequestItem = {
  id: string;
  submitted_name: string;
  website: string | null;
  industry: string | null;
  note: string | null;
  created_at: string;
  /** Close existing companies, so a variant spelling is merged rather
   *  than created twice. */
  possible_matches: CompanySummary[];
};

export type CompanyRequestDecision = "APPROVE" | "MERGE" | "REJECT";

export function fetchCompanyRequests(cookie?: string): Promise<CompanyRequestItem[]> {
  return apiRequest<CompanyRequestItem[]>("/admin/company-requests", {
    cache: "no-store",
    ...(cookie ? { cookie } : {}),
  });
}

export function decideCompanyRequest(
  requestId: string,
  body: { decision: CompanyRequestDecision; company_slug?: string; note?: string },
) {
  return apiRequest<{ id: string; status: string; company_slug: string | null }>(
    `/admin/company-requests/${requestId}/decision`,
    { method: "POST", body },
  );
}

/** One decision across a quick log. Approval is partial verification and
 *  covers only the lines that passed the auto-checks; flagged lines stay in
 *  the queue for one-by-one review. */
export function decideBatch(
  batchId: string,
  body: { decision: "PARTIALLY_VERIFY" | "REJECT"; note?: string },
) {
  return apiRequest<{ decided: number; left_for_review: number }>(
    `/admin/report-batches/${batchId}/decision`,
    { method: "POST", body },
  );
}
