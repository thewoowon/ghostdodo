import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";
import {
  DodoEgg,
  EvidenceStamp,
  FieldNotebook,
  ResponseSignal,
  SilenceSignal,
} from "@/components/brand/svg/marks";
import { CompanySearch } from "@/components/search/CompanySearch";

import styles from "./page.module.css";

/**
 * Landing page.
 *
 * The hero copy is fixed by the handoff (docs/10) and must be preserved
 * verbatim. Note what this page does NOT do: it shows no company rankings.
 * The archive is being built, and inventing leaderboards from demo fixtures
 * would violate the "no fake data" rule (docs/03 §2).
 */
export default function HomePage() {
  return (
    <>
      <section className={styles.hero}>
        <div className={`gd-shell ${styles.heroInner}`}>
          <DodoMark size={92} className={styles.heroMark} aria-hidden />

          <h1 className={styles.h1}>
            지원하기 전에,
            <br />
            답은 해주는 회사인지 확인하세요.
          </h1>

          <p className={styles.lede}>
            <strong>답장이 멸종된 회사들을 기록합니다.</strong>
            <br />
            지원자들이 직접 남긴 채용 응답 기록을 바탕으로 회사별 결과 통보율과
            응답 시간을 확인하세요.
          </p>

          <div className={styles.searchSlot}>
            <CompanySearch size="hero" />
          </div>

          <div className={styles.ctas}>
            <Link href="/search" className={styles.primaryCta}>
              회사 검색하기
            </Link>
            <Link href="/report/new" className={styles.secondaryCta}>
              내 경험 기록하기
            </Link>
          </div>
        </div>
      </section>

      {/*
        "오늘의 관측" and the two balanced company blocks are intentionally
        absent until real qualified data exists. Until then this onboarding
        state explains what is being built, rather than filling the space
        with numbers nobody has earned.
      */}
      <section className={`gd-shell ${styles.section}`}>
        <div className={styles.buildingCard}>
          <DodoEgg size={30} className={styles.buildingMark} />
          <div>
            <h2 className={styles.buildingTitle}>도감을 만들고 있습니다</h2>
            <p className={styles.buildingBody}>
              GhostDodo는 지원자가 직접 남긴 기록만으로 지표를 만듭니다. 아직
              표본이 충분하지 않은 회사는 순위나 비율 대신{" "}
              <strong>표본 부족</strong>으로 표시됩니다. 추측한 숫자는 보여드리지
              않습니다.
            </p>
          </div>
        </div>
      </section>

      <section className={`gd-shell ${styles.section}`}>
        <h2 className={styles.sectionTitle}>무엇을 기록하나요</h2>
        <p className={styles.sectionLede}>
          감정이 아니라 사건을 기록합니다. 언제 지원했고, 어느 단계까지 갔고,
          회사가 결과를 언제까지 알려주겠다고 했는지, 그리고 실제로 답이
          왔는지를 구조화된 형태로 남깁니다.
        </p>

        <ul className={styles.pillars}>
          <li className={styles.pillar}>
            <ResponseSignal size={26} className={styles.pillarMarkAlive} />
            <h3 className={styles.pillarTitle}>결과 통보율</h3>
            <p className={styles.pillarBody}>
              합격이든 불합격이든 <strong>명시적으로 결과를 알려준 비율</strong>
              입니다. 불합격 통보도 성실한 응답으로 계산합니다.
            </p>
          </li>
          <li className={styles.pillar}>
            <SilenceSignal size={26} className={styles.pillarMarkExtinct} />
            <h3 className={styles.pillarTitle}>단계별 침묵</h3>
            <p className={styles.pillarBody}>
              침묵을 하나로 묶지 않습니다. 서류 단계의 무응답과 최종 면접 후의
              무응답은 다른 사건으로 기록합니다.
            </p>
          </li>
          <li className={styles.pillar}>
            <FieldNotebook size={26} className={styles.pillarMark} />
            <h3 className={styles.pillarTitle}>약속 이행</h3>
            <p className={styles.pillarBody}>
              회사가 직접 말한 결과 안내 예정일이 있는 경우, 그 약속이 지켜졌는지
              별도로 집계합니다.
            </p>
          </li>
        </ul>
      </section>

      <section className={`gd-shell ${styles.section}`}>
        <div className={styles.trustBlock}>
          <EvidenceStamp size={28} className={styles.trustMark} />
          <div>
            <h2 className={styles.sectionTitle}>검증은 이렇게 합니다</h2>
            <ol className={styles.steps}>
              <li>
                <strong>구조화된 기록</strong> — 자유 서술이 아니라 날짜·단계·결과
                항목으로 입력받습니다.
              </li>
              <li>
                <strong>비공개 자료 첨부</strong> — 결과 메일 스크린샷 같은 자료는
                검증에만 사용되며 공개되지 않습니다.
              </li>
              <li>
                <strong>검토</strong> — 운영진이 자료와 기록의 일관성을 확인합니다.
              </li>
              <li>
                <strong>표본 기준 충족 시 공개</strong> — 표본이 적으면 비율을
                공개하지 않습니다.
              </li>
            </ol>
            <Link href="/methodology" className={styles.inlineLink}>
              측정 기준 자세히 보기
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
