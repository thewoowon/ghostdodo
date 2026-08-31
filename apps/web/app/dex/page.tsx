import type { Metadata } from "next";
import Link from "next/link";

import { DodoEgg, FossilMark, ResponseSignal } from "@/components/brand/svg/marks";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "GhostDodo 도감",
  description: "관측된 회사들의 채용 응답 패턴을 둘러보세요.",
  alternates: { canonical: "/dex" },
};

/**
 * The 도감 exploration surface.
 *
 * Leaderboards stay closed until enough companies clear the publishable
 * sample bar. Ranking demo fixtures — or real companies on thin data — would
 * be exactly the fake-ranking failure the handoff forbids (docs/03 §2).
 */
export default function DexPage() {
  const views = [
    { icon: "response", title: "답장이 살아있는 회사", body: "결과 통보율이 높은 회사" },
    { icon: "fossil", title: "관찰이 필요한 회사", body: "무응답 기록이 누적된 회사" },
    { icon: "egg", title: "새로 등록된 회사", body: "최근 도감에 추가된 회사" },
  ] as const;

  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <h1 className={styles.title}>GhostDodo 도감</h1>
        <p className={styles.lede}>
          관측된 회사들의 채용 응답 패턴을 분류해 둘러보는 곳입니다.
        </p>
      </header>

      <div className={styles.notice}>
        <DodoEgg size={30} className={styles.noticeMark} />
        <div>
          <h2 className={styles.noticeTitle}>아직 도감을 여는 중입니다</h2>
          <p className={styles.noticeBody}>
            공개 기준을 충족한 회사가 충분히 쌓이면 분류별 목록을 공개합니다.
            표본이 부족한 상태에서 순위를 만들면 그 순위는 회사에 대한 사실이
            아니라 우연이 됩니다. 그때까지는 회사를 직접 검색해 개별 기록을
            확인해 주세요.
          </p>
          <Link href="/search" className={styles.noticeLink}>
            회사 검색하기
          </Link>
        </div>
      </div>

      <section aria-label="공개 예정 분류">
        <h2 className={styles.sectionTitle}>공개 예정 분류</h2>
        <ul className={styles.views}>
          {views.map((view) => (
            <li key={view.title} className={styles.view}>
              {view.icon === "response" && (
                <ResponseSignal size={24} className={styles.viewMarkAlive} />
              )}
              {view.icon === "fossil" && (
                <FossilMark size={24} className={styles.viewMarkExtinct} />
              )}
              {view.icon === "egg" && <DodoEgg size={24} className={styles.viewMark} />}
              <h3 className={styles.viewTitle}>{view.title}</h3>
              <p className={styles.viewBody}>{view.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
