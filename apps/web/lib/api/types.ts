/** Response shapes from the FastAPI service. Mirrors specs/API_CONTRACT.md. */
import type {
  ApplicationSource,
  CommunicationChannel,
  EmploymentType,
  HiringStage,
  MetricEligibility,
  MetricWindow,
  Outcome,
  RoleCategory,
  VerificationStatus,
} from "@/lib/domain";

export type CompanySummary = {
  id: string;
  slug: string;
  display_name_ko: string;
  name_en: string | null;
  industry: string | null;
  public_report_count: number;
  /** Fixture data. The UI must label it as sample content. */
  is_demo: boolean;
};

export type CompanyDetail = CompanySummary & {
  legal_name_ko: string;
  aliases: string[];
  website: string | null;
  size_band: string;
  claim_state: string;
};

export type StageMetrics = {
  stage: HiringStage;
  qualified_n: number;
  response_rate: number | null;
  ghost_rate: number | null;
  median_response_days: number | null;
};

/**
 * Every rate is nullable. Below the publishable sample bar the API returns
 * `null` rather than a small-sample percentage, and the UI must render
 * `표본 부족` instead of inventing a number.
 */
export type CompanyMetrics = {
  company_id: string;
  window: MetricWindow;
  window_start: string | null;
  window_end: string | null;
  eligibility: MetricEligibility;
  qualified_n: number;
  verified_ratio: number;
  response_rate: number | null;
  ghost_rate: number | null;
  broken_promise_rate: number | null;
  median_response_days: number | null;
  promised_timeline_n: number;
  stage_breakdown: StageMetrics[];
  methodology_version: string;
  computed_at: string | null;
};

/** Cursor page. `next_cursor` is null on the last page. */
export type Paged<T> = {
  items: T[];
  next_cursor: string | null;
};

/**
 * A linked job posting.
 *
 * Deliberately carries no rate. A posting says a company is hiring; only
 * qualified reports say how it answers, so a card can never imply a number
 * the sample cannot support.
 */
export type JobCard = {
  id: string;
  title: string;
  role_category: RoleCategory | null;
  employment_type: EmploymentType | null;
  location: string | null;
  source: ApplicationSource;
  /** The board's own name when the importer recorded one. */
  source_label: string | null;
  closes_on: string | null;
  is_open: boolean;
  observed_at: string;
  /** Null when the stored URL is not a linkable http(s) address — the card
   *  then renders without an apply CTA rather than with a dead link. */
  apply_url: string | null;
  company: CompanySummary;
};

export type JobDetail = JobCard & {
  last_checked_at: string | null;
};

export type OutboundClickAccepted = {
  apply_url: string;
  recorded: boolean;
};

/** Public report card. Deliberately has no reporter field. */
export type PublicReportCard = {
  id: string;
  role_category: RoleCategory;
  employment_type: EmploymentType;
  furthest_stage: HiringStage;
  application_date: string;
  promised_result: boolean;
  promised_result_date: string | null;
  result_received: boolean;
  result_received_at: string | null;
  outcome: Outcome;
  verification_status: VerificationStatus;
  context_tags: string[];
  free_context: string | null;
  helpful_count: number;
};

export type OwnReport = PublicReportCard & {
  company_id: string;
  submitted_at: string | null;
  created_at: string;
  evidence_count: number;
};

/** A row of `/me/reports`: the contributor's own record, so it names the
 *  company. Public cards never carry this pairing with a reporter. */
export type MyReport = OwnReport & {
  company_slug: string;
  company_name: string;
};

export type AuthProviders = {
  /** False until Google credentials are configured on the API. The sign-in
   *  page renders its button from this, never from its own env, so a
   *  misconfigured API cannot produce a button that leads nowhere. */
  google: boolean;
  magic_link: boolean;
};

export type SignInAccepted = {
  message: string;
  /** Returned outside production so local development needs no mail server. */
  dev_token: string | null;
};

export type EarnedBadge = {
  code: string;
  /** Labelled by the API, so a new badge needs no front-end deploy. */
  label: string;
  description: string;
};

export type Profile = {
  id: string;
  handle: string;
  role: string;
  rank: string;
  reputation_score: number;
  credit_balance: number;
  verified_contribution_count: number;
  trust_state: string;
  badges: EarnedBadge[];
  created_at: string;
};

/** One append-only ledger line. Reputation and credit share the shape. */
export type LedgerEntry = {
  id: string;
  event_type: string;
  delta: number;
  balance_after: number;
  created_at: string;
};

export type SessionUser = {
  id: string;
  handle: string;
  role: string;
  reputation_score: number;
  credit_balance: number;
  rank: string;
};

export type ReportInput = {
  company_id: string;
  role_title: string;
  role_category: RoleCategory;
  employment_type: EmploymentType;
  source: ApplicationSource;
  application_date: string;
  furthest_stage: HiringStage;
  last_company_interaction_at?: string | null;
  promised_result: boolean;
  promised_result_date?: string | null;
  promised_window_end_date?: string | null;
  result_received: boolean;
  result_received_at?: string | null;
  result_channel?: CommunicationChannel | null;
  outcome: Outcome;
  context_tags?: string[];
  free_context?: string | null;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    request_id: string;
    details: Record<string, unknown>;
  };
};

export type Methodology = {
  version: string;
  stage_thresholds: Record<
    HiringStage,
    { silence_days: number; analytic_weight: number }
  >;
  promise_grace_days: number;
  eligibility: Record<
    string,
    { min_qualified_n: number; min_verified_ratio: number }
  >;
  recency_windows: string[];
  default_public_window: string;
};
