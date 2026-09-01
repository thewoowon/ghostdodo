/**
 * The profile surface.
 *
 * Phase 4 shipped working ledgers, ranks and a badge table with nothing to
 * read them. What matters in the UI layer is that the ledger stays legible
 * as a ledger — every line explains the balance beside it — and that the
 * ranks and event labels stay pinned to the API's wire values.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LedgerList } from "@/components/me/LedgerList";
import { RankCrest } from "@/components/me/RankCrest";
import {
  CREDIT_EVENT_LABELS,
  RANK_LABELS,
  REPUTATION_EVENT_LABELS,
  REPUTATION_RANKS,
} from "@/lib/domain";

const ENTRIES = [
  {
    id: "1",
    event_type: "REPORT_VERIFIED",
    delta: 20,
    balance_after: 25,
    created_at: "2026-08-20T00:00:00Z",
  },
  {
    id: "2",
    event_type: "REPORT_SUBMITTED_COMPLETE",
    delta: 5,
    balance_after: 5,
    created_at: "2026-08-15T00:00:00Z",
  },
];

describe("LedgerList", () => {
  it("shows each line's own delta and the balance it produced", () => {
    // The current score has to be explainable from the rows above it, which
    // is the whole point of an append-only ledger.
    render(<LedgerList entries={ENTRIES} kind="reputation" />);

    const rows = screen.getAllByRole("listitem");
    expect(within(rows[0]!).getByText("+20")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("25")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("+5")).toBeInTheDocument();
  });

  it("signs a deduction rather than hiding it", () => {
    render(
      <LedgerList
        entries={[
          {
            id: "3",
            event_type: "REPORT_REVERSED",
            delta: -25,
            balance_after: 0,
            created_at: "2026-08-21T00:00:00Z",
          },
        ]}
        kind="reputation"
      />,
    );
    expect(screen.getByText("-25")).toBeInTheDocument();
    expect(screen.getByText("기록 검증 철회")).toBeInTheDocument();
  });

  it("falls back to the raw event type rather than rendering nothing", () => {
    render(
      <LedgerList
        entries={[
          {
            id: "4",
            event_type: "SOME_FUTURE_EVENT",
            delta: 1,
            balance_after: 1,
            created_at: "2026-08-21T00:00:00Z",
          },
        ]}
        kind="reputation"
      />,
    );
    expect(screen.getByText("SOME_FUTURE_EVENT")).toBeInTheDocument();
  });

  it("uses the credit vocabulary for the credit ledger", () => {
    render(
      <LedgerList
        entries={[
          {
            id: "5",
            event_type: "VERIFICATION_BONUS",
            delta: 20,
            balance_after: 20,
            created_at: "2026-08-21T00:00:00Z",
          },
        ]}
        kind="credit"
      />,
    );
    expect(screen.getByText("검증 보너스")).toBeInTheDocument();
  });

  it("says so plainly when there is nothing yet", () => {
    render(<LedgerList entries={[]} kind="reputation" />);
    expect(screen.getByText(/아직 평판 내역이 없습니다/)).toBeInTheDocument();
  });
});

describe("labels", () => {
  it("covers every rank the API can send", () => {
    for (const rank of REPUTATION_RANKS) {
      expect(RANK_LABELS[rank]).toBeTruthy();
    }
  });

  it("never describes a reward in terms of what a report said", () => {
    // docs/07 §2: standing is earned by completeness and verification, not by
    // reporting something negative. The copy must not drift from that.
    const rewardCopy = Object.entries(REPUTATION_EVENT_LABELS)
      .filter(([code]) => !["REPORT_REVERSED", "MODERATION_SANCTION"].includes(code))
      .map(([, label]) => label)
      .join(" ");
    for (const forbidden of ["무응답", "미응답", "폭로", "고발"]) {
      expect(rewardCopy).not.toContain(forbidden);
    }
  });

  it("never describes credit in monetary terms", () => {
    // docs/07 §1: product utility, not currency. No cash-out language, ever.
    const copy = Object.values(CREDIT_EVENT_LABELS).join(" ");
    for (const forbidden of ["현금", "원", "출금", "환전", "코인"]) {
      expect(copy).not.toContain(forbidden);
    }
  });
});

describe("RankCrest", () => {
  it("names the rank for assistive technology", () => {
    render(<RankCrest rank="ARCHIVIST" />);
    expect(screen.getByRole("img", { name: "아키비스트 등급" })).toBeInTheDocument();
  });

  it("fills one more tick at each tier", () => {
    const { container: low } = render(<RankCrest rank="OBSERVER" />);
    const { container: high } = render(<RankCrest rank="DODO_RANGER" />);
    const filled = (el: HTMLElement) =>
      el.querySelectorAll('circle[r="2.6"]').length;
    expect(filled(low)).toBe(1);
    expect(filled(high)).toBe(REPUTATION_RANKS.length);
  });
});
