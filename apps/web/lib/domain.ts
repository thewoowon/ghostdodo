/**
 * Domain types mirroring `apps/api/app/shared/enums`.
 *
 * These are wire values, not display strings — they must stay byte-identical
 * to the Python enums. Korean labels live in `LABELS` below so a value change
 * and a copy change can never be confused for one another.
 */

export const HIRING_STAGES = [
  "APPLICATION",
  "DOCUMENT_SCREENING",
  "TEST",
  "ASSIGNMENT",
  "INTERVIEW_1",
  "INTERVIEW_2_PLUS",
  "FINAL_INTERVIEW",
  "OFFER_COMPENSATION",
] as const;
export type HiringStage = (typeof HIRING_STAGES)[number];

export const STAGE_LABELS: Record<HiringStage, string> = {
  APPLICATION: "지원",
  DOCUMENT_SCREENING: "서류",
  TEST: "코딩/필기",
  ASSIGNMENT: "과제",
  INTERVIEW_1: "1차 면접",
  INTERVIEW_2_PLUS: "2차/추가 면접",
  FINAL_INTERVIEW: "최종 면접",
  OFFER_COMPENSATION: "처우/오퍼",
};

export const ROLE_CATEGORIES = [
  "SOFTWARE_ENGINEERING",
  "DATA",
  "DESIGN",
  "PRODUCT",
  "MARKETING",
  "SALES",
  "OPERATIONS",
  "HR",
  "FINANCE",
  "CUSTOMER_SUPPORT",
  "RESEARCH",
  "MANUFACTURING",
  "OTHER",
] as const;
export type RoleCategory = (typeof ROLE_CATEGORIES)[number];

export const ROLE_LABELS: Record<RoleCategory, string> = {
  SOFTWARE_ENGINEERING: "개발",
  DATA: "데이터",
  DESIGN: "디자인",
  PRODUCT: "프로덕트",
  MARKETING: "마케팅",
  SALES: "영업",
  OPERATIONS: "운영",
  HR: "인사",
  FINANCE: "재무",
  CUSTOMER_SUPPORT: "고객지원",
  RESEARCH: "연구",
  MANUFACTURING: "생산",
  OTHER: "기타",
};

export const EMPLOYMENT_TYPES = [
  "FULL_TIME",
  "CONTRACT",
  "INTERN",
  "PART_TIME",
  "FREELANCE",
  "DISPATCH",
] as const;
export type EmploymentType = (typeof EMPLOYMENT_TYPES)[number];

export const EMPLOYMENT_LABELS: Record<EmploymentType, string> = {
  FULL_TIME: "정규직",
  CONTRACT: "계약직",
  INTERN: "인턴",
  PART_TIME: "파트타임",
  FREELANCE: "프리랜서",
  DISPATCH: "파견",
};

export const APPLICATION_SOURCES = [
  "COMPANY_SITE",
  "SARAMIN",
  "JOBKOREA",
  "WANTED",
  "JUMPIT",
  "PROGRAMMERS",
  "ROCKETPUNCH",
  "REMEMBER",
  "LINKEDIN",
  "REFERRAL",
  "RECRUITER_OUTREACH",
  "OTHER",
] as const;
export type ApplicationSource = (typeof APPLICATION_SOURCES)[number];

export const SOURCE_LABELS: Record<ApplicationSource, string> = {
  COMPANY_SITE: "회사 채용 페이지",
  SARAMIN: "사람인",
  JOBKOREA: "잡코리아",
  WANTED: "원티드",
  JUMPIT: "점핏",
  PROGRAMMERS: "프로그래머스",
  ROCKETPUNCH: "로켓펀치",
  REMEMBER: "리멤버",
  LINKEDIN: "링크드인",
  REFERRAL: "지인 추천",
  RECRUITER_OUTREACH: "리크루터 제안",
  OTHER: "기타",
};

export const OUTCOMES = ["PASSED", "REJECTED", "WITHDREW", "UNKNOWN"] as const;
export type Outcome = (typeof OUTCOMES)[number];

export const OUTCOME_LABELS: Record<Outcome, string> = {
  PASSED: "합격",
  REJECTED: "불합격",
  WITHDREW: "지원 철회",
  UNKNOWN: "결과 미수신",
};

export const CHANNELS = [
  "EMAIL",
  "SMS",
  "PHONE",
  "JOB_BOARD",
  "MESSENGER",
  "IN_PERSON",
  "OTHER",
] as const;
export type CommunicationChannel = (typeof CHANNELS)[number];

export const CHANNEL_LABELS: Record<CommunicationChannel, string> = {
  EMAIL: "이메일",
  SMS: "문자",
  PHONE: "전화",
  JOB_BOARD: "채용 사이트",
  MESSENGER: "메신저",
  IN_PERSON: "대면",
  OTHER: "기타",
};

export type VerificationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "AUTO_CHECKED"
  | "NEEDS_REVIEW"
  | "VERIFIED"
  | "PARTIALLY_VERIFIED"
  | "REJECTED"
  | "DISPUTED"
  | "REDACTED"
  | "REMOVED";

export const VERIFICATION_LABELS: Record<VerificationStatus, string> = {
  DRAFT: "작성 중",
  SUBMITTED: "제출됨",
  AUTO_CHECKED: "자동 검사 완료",
  NEEDS_REVIEW: "검토 대기",
  VERIFIED: "검증됨",
  PARTIALLY_VERIFIED: "부분 검증",
  REJECTED: "반려됨",
  DISPUTED: "이의 제기됨",
  REDACTED: "일부 삭제",
  REMOVED: "삭제됨",
};

export type MetricEligibility =
  | "INSUFFICIENT_DATA"
  | "EARLY_SIGNAL"
  | "PUBLISHABLE"
  | "HIGH_CONFIDENCE";

export type MetricWindow = "6m" | "12m" | "all";

export const WINDOW_LABELS: Record<MetricWindow, string> = {
  "6m": "최근 6개월",
  "12m": "최근 12개월",
  all: "전체 기간",
};

/**
 * Reputation ranks. Names are from docs/07 §3 — original, and deliberately
 * about observation and record-keeping rather than status over other people.
 */
export const REPUTATION_RANKS = [
  "OBSERVER",
  "EXPLORER",
  "RECORDER",
  "VERIFIER",
  "ARCHIVIST",
  "DODO_RANGER",
] as const;
export type ReputationRank = (typeof REPUTATION_RANKS)[number];

export const RANK_LABELS: Record<ReputationRank, string> = {
  OBSERVER: "관찰자",
  EXPLORER: "탐사자",
  RECORDER: "기록자",
  VERIFIER: "검증자",
  ARCHIVIST: "아키비스트",
  DODO_RANGER: "도도 레인저",
};

/**
 * What each ledger line means, in plain Korean.
 *
 * Every positive entry describes completeness, evidence, or corroboration —
 * none of them describes what a report said about a company. That is the
 * award table's rule (docs/07 §2) surfacing in the copy.
 */
export const REPUTATION_EVENT_LABELS: Record<string, string> = {
  REPORT_SUBMITTED_COMPLETE: "기록 제출 (내용 충실)",
  REPORT_VERIFIED: "기록 검증 완료",
  EVIDENCE_VERIFIED: "증빙 확인",
  REPORT_CORROBORATED: "다른 기록과 교차 확인",
  FACTUAL_CORRECTION_ACCEPTED: "정정 요청 반영",
  COMPANY_METADATA_ACCEPTED: "회사 정보 보완",
  PII_FLAG_ACCEPTED: "개인정보 신고 반영",
  HELPFUL_COMMUNITY_ANSWER: "도움이 된 답변",
  REPORT_REVERSED: "기록 검증 철회",
  MODERATION_SANCTION: "운영 제재",
};

export const CREDIT_EVENT_LABELS: Record<string, string> = {
  CONTRIBUTION_REWARD: "기여 보상",
  VERIFICATION_BONUS: "검증 보너스",
  FIRST_OBSERVATION_BONUS: "최초 관측 보너스",
  COSMETIC_PURCHASE: "꾸미기 사용",
  ADJUSTMENT: "조정",
  REVERSAL: "회수",
};

export const TRUST_STATE_LABELS: Record<string, string> = {
  NEW: "신규",
  ACTIVE: "정상",
  RESTRICTED: "제한",
  SUSPENDED: "정지",
};
