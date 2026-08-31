/**
 * Metric presentation rules.
 *
 * The single most important rule in the product's UI: a rate that the API
 * returned as `null` is NOT zero, NOT unknown-but-probably-bad, and must
 * never be rendered as a number. `formatRate` returns null so callers are
 * forced by the type system to handle the suppressed case.
 */
import type { MetricEligibility } from "@/lib/domain";

export function formatRate(value: number | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  return `${Math.round(value * 100)}%`;
}

export function formatDays(value: number | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  // One decimal only when it changes the reading.
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}일`;
}

export const ELIGIBILITY_LABELS: Record<MetricEligibility, string> = {
  INSUFFICIENT_DATA: "표본 부족",
  EARLY_SIGNAL: "초기 신호",
  PUBLISHABLE: "공개 기준 충족",
  HIGH_CONFIDENCE: "표본 충분",
};

export const ELIGIBILITY_NOTES: Record<MetricEligibility, string> = {
  INSUFFICIENT_DATA: "아직 판정하기 이릅니다. 관측 표본이 부족합니다.",
  EARLY_SIGNAL: "관측이 시작됐지만 아직 공개 지표로 판정하지 않습니다.",
  PUBLISHABLE: "공개 기준을 충족한 표본입니다.",
  HIGH_CONFIDENCE: "표본과 검증 비율이 모두 충분합니다.",
};

export function canPublishRates(eligibility: MetricEligibility): boolean {
  return eligibility === "PUBLISHABLE" || eligibility === "HIGH_CONFIDENCE";
}

/**
 * Response-behaviour verdict shown on a company page.
 *
 * Positive and negative verdicts get equal visual weight by design — the
 * product surfaces companies that answer as prominently as those that do
 * not (README principle 3).
 */
export type ResponseVerdict = {
  label: string;
  tone: "alive" | "watch" | "extinct" | "unknown";
  note: string;
};

export function responseVerdict(
  responseRate: number | null,
  eligibility: MetricEligibility,
): ResponseVerdict {
  if (!canPublishRates(eligibility) || responseRate === null) {
    return {
      label: "판정 보류",
      tone: "unknown",
      note: ELIGIBILITY_NOTES[eligibility],
    };
  }
  if (responseRate >= 0.85) {
    return {
      label: "답장 생존",
      tone: "alive",
      note: "대부분의 지원자가 결과를 통보받았습니다.",
    };
  }
  if (responseRate >= 0.6) {
    return {
      label: "부분 응답",
      tone: "watch",
      note: "결과를 받지 못한 지원자가 일부 있습니다.",
    };
  }
  if (responseRate >= 0.35) {
    return {
      label: "관찰 필요",
      tone: "watch",
      note: "결과 통보율이 낮은 편입니다.",
    };
  }
  return {
    label: "멸종위기",
    tone: "extinct",
    note: "결과를 통보받지 못한 지원자가 많습니다.",
  };
}

/** Korean date formatting. Storage is UTC; presentation is local (docs/05 §3). */
export function formatKoreanDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Asia/Seoul",
  }).format(date);
}

export function formatShortDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Seoul",
  }).format(date);
}
