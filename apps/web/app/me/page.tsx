import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { DodoEgg, EvidenceStamp, FieldNotebook } from "@/components/brand/svg/marks";
import { LedgerList } from "@/components/me/LedgerList";
import { RankCrest } from "@/components/me/RankCrest";
import { load } from "@/lib/api/load";
import { getCreditLedger, getProfile, getReputationLedger } from "@/lib/api/queries";
import { RANK_LABELS, TRUST_STATE_LABELS, type ReputationRank } from "@/lib/domain";
import { formatKoreanDate } from "@/lib/format/metrics";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "내 활동",
  robots: { index: false, follow: false },
};

// Standing changes when a moderator acts, so it is never served from cache.
export const dynamic = "force-dynamic";

export default async function MePage() {
  const cookieHeader = (await cookies()).toString();

  const result = await load(() =>
    Promise.all([
      getProfile(cookieHeader),
      getReputationLedger(cookieHeader),
      getCreditLedger(cookieHeader),
    ]),
  );

  if (!result.ok) {
    if (result.failure === "unauthenticated") {
      return (
        <div className={`gd-shell ${styles.gate}`}>
          <DodoEgg size={34} className={styles.gateMark} />
          <h1 className={styles.gateTitle}>로그인이 필요합니다</h1>
          <p className={styles.gateBody}>내 활동은 로그인 후 볼 수 있습니다.</p>
          <Link href="/sign-in?next=%2Fme" className={styles.gateLink}>
            로그인하기
          </Link>
        </div>
      );
    }
    return (
      <div className={`gd-shell ${styles.gate}`}>
        <h1 className={styles.gateTitle}>지금은 불러올 수 없습니다</h1>
        <p className={styles.gateBody}>
          일시적인 연결 문제입니다. 잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  const [profile, reputation, credits] = result.data;
  const rank = profile.rank as ReputationRank;
  const joined = formatKoreanDate(profile.created_at);

  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.identity}>
        <RankCrest rank={rank} />
        <div className={styles.identityText}>
          <h1 className={styles.handle}>{profile.handle}</h1>
          <p className={styles.rankLine}>
            <strong>{RANK_LABELS[rank] ?? profile.rank}</strong>
            {joined ? ` · ${joined} 합류` : ""}
            {profile.trust_state !== "ACTIVE" && (
              <span className={styles.trust}>
                {TRUST_STATE_LABELS[profile.trust_state] ?? profile.trust_state}
              </span>
            )}
          </p>
          {/* The handle is the only public identity; say so where someone
              can actually see it next to their real activity. */}
          <p className={styles.pseudonym}>
            공개되는 이름은 이 별명뿐입니다. 이메일과 실명은 회사에도, 다른
            이용자에게도 표시되지 않습니다.
          </p>
        </div>
      </header>

      <section className={styles.stats} aria-label="활동 요약">
        <div className={styles.stat}>
          <span className={styles.statLabel}>평판 점수</span>
          <span className={`${styles.statValue} gd-tabular`}>
            {profile.reputation_score}
          </span>
          <span className={styles.statNote}>
            기록의 충실도와 검증으로 쌓입니다
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>도도 크레딧</span>
          <span className={`${styles.statValue} gd-tabular`}>
            {profile.credit_balance}
          </span>
          {/* docs/07 §1: never monetary, and never described as if it were. */}
          <span className={styles.statNote}>
            서비스 안에서만 쓰는 기여 포인트입니다. 현금화되지 않습니다
          </span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>검증된 기록</span>
          <span className={`${styles.statValue} gd-tabular`}>
            {profile.verified_contribution_count}
          </span>
          <span className={styles.statNote}>
            <Link href="/me/reports" className={styles.statLink}>
              내 기록 보기
            </Link>
          </span>
        </div>
      </section>

      {/* The rule that governs the whole system, said once, where someone is
          looking at their own score. */}
      <p className={styles.principle}>
        회사가 답을 줬든 주지 않았든 점수는 같습니다. 평판은 기록이 얼마나
        충실하고 검증 가능한지로만 쌓이며, 부정적인 내용을 많이 남긴다고 더
        오르지 않습니다.{" "}
        <Link href="/methodology" className={styles.statLink}>
          측정 기준
        </Link>
      </p>

      <section aria-label="배지">
        <h2 className={styles.h2}>
          <EvidenceStamp size={20} className={styles.h2Mark} />
          배지
        </h2>
        {profile.badges.length === 0 ? (
          <p className={styles.emptyBadges}>
            아직 받은 배지가 없습니다. 첫 기록이 검증을 마치면 배지가
            추가됩니다.
          </p>
        ) : (
          <ul className={styles.badges}>
            {profile.badges.map((badge) => (
              <li key={badge.code} className={styles.badge}>
                <span className={styles.badgeLabel}>{badge.label}</span>
                <span className={styles.badgeBody}>{badge.description}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="평판 기록">
        <h2 className={styles.h2}>
          <FieldNotebook size={20} className={styles.h2Mark} />
          평판 기록
        </h2>
        <LedgerList entries={reputation} kind="reputation" />
      </section>

      <section aria-label="크레딧 기록">
        <h2 className={styles.h2}>도도 크레딧 기록</h2>
        <LedgerList entries={credits} kind="credit" />
      </section>
    </div>
  );
}
