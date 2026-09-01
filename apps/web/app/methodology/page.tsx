import type { Metadata } from "next";

import { RadarRipple } from "@/components/brand/svg/marks";
import { ApiUnavailableError } from "@/lib/api/client";
import { getMethodology } from "@/lib/api/queries";
import { STAGE_LABELS, type HiringStage } from "@/lib/domain";
import { ELIGIBILITY_LABELS } from "@/lib/format/metrics";
import type { MetricEligibility } from "@/lib/domain";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "측정 기준",
  description:
    "GhostDodo가 결과 통보율과 무응답률을 어떻게 계산하는지, 어떤 기록을 집계에서 제외하는지 설명합니다.",
  alternates: { canonical: "/methodology" },
};

const ELIGIBILITY_ORDER: MetricEligibility[] = [
  "EARLY_SIGNAL",
  "PUBLISHABLE",
  "HIGH_CONFIDENCE",
];

/**
 * Public methodology.
 *
 * Rendered from the API's own configuration rather than hand-written
 * numbers, so this page can never describe thresholds the calculations do
 * not actually use.
 */
export default async function MethodologyPage() {
  let methodology = null;
  try {
    methodology = await getMethodology();
  } catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
  }

  return (
    <article className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <RadarRipple size={30} className={styles.headerMark} />
        <h1 className={styles.title}>측정 기준</h1>
        {methodology && (
          <p className={styles.version}>
            현재 적용 버전{" "}
            <code className={styles.code}>{methodology.version}</code>
          </p>
        )}
      </header>

      <section className={styles.section}>
        <h2 className={styles.h2}>침묵을 바로 침묵이라 부르지 않습니다</h2>
        <p className={styles.body}>
          지원자가 결과를 받지 못했다고 해서 곧바로 무응답으로 집계하지 않습니다.
          단계별로 정해진 관측 기간이 지나야 하나의 관측으로 인정합니다. 채용
          과정이 원래 오래 걸리는 단계일수록 더 긴 기간을 기다립니다.
        </p>

        {methodology ? (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className="gd-sr-only">단계별 관측 기간</caption>
              <thead>
                <tr>
                  <th scope="col">단계</th>
                  <th scope="col" className={styles.numeric}>관측 기간</th>
                </tr>
              </thead>
              <tbody>
                {(Object.keys(methodology.stage_thresholds) as HiringStage[]).map(
                  (stage) => (
                    <tr key={stage}>
                      <th scope="row">{STAGE_LABELS[stage]}</th>
                      <td className={`${styles.numeric} gd-tabular`}>
                        {methodology.stage_thresholds[stage].silence_days}일
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <p className={styles.unavailable}>
            지금은 기준 값을 불러올 수 없습니다.
          </p>
        )}

        {methodology && (
          <p className={styles.note}>
            회사가 결과 안내 예정일을 직접 밝힌 경우에는 단계별 기간 대신 그
            예정일에{" "}
            <strong className="gd-tabular">
              {methodology.promise_grace_days}일
            </strong>
            의 유예를 더한 날짜를 기준으로 삼습니다.
          </p>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.h2}>불합격 통보도 응답입니다</h2>
        <p className={styles.body}>
          결과 통보율은 <strong>명시적인 결과를 전달받은 비율</strong>입니다.
          합격이든 불합격이든, 회사가 지원자에게 결과를 알렸다면 성실한 응답으로
          계산합니다. 고스트도도는 채용 결과가 아니라 채용 커뮤니케이션을
          측정합니다.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.h2}>집계에서 제외하는 기록</h2>
        <ul className={styles.list}>
          <li>지원자가 스스로 전형을 포기한 경우</li>
          <li>관측 기간이 아직 지나지 않은 경우</li>
          <li>같은 지원자가 같은 회사·단계에 중복 등록한 경우</li>
          <li>검증되지 않았거나 반려된 기록</li>
          <li>시점 정보가 부족해 경과를 계산할 수 없는 경우</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2 className={styles.h2}>표본이 적으면 숫자를 보여주지 않습니다</h2>
        <p className={styles.body}>
          기록 2건으로 만든 100%는 회사에 대한 사실이 아닙니다. 아래 기준을
          충족하지 못한 회사는 비율 대신 <strong>표본 부족</strong>으로
          표시하며, 모든 지표에는 표본 수와 기간을 함께 적습니다.
        </p>

        {methodology && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className="gd-sr-only">공개 기준</caption>
              <thead>
                <tr>
                  <th scope="col">상태</th>
                  <th scope="col" className={styles.numeric}>최소 관측 수</th>
                  <th scope="col" className={styles.numeric}>최소 검증 비율</th>
                </tr>
              </thead>
              <tbody>
                {ELIGIBILITY_ORDER.map((state) => {
                  const bar = methodology.eligibility[state];
                  if (!bar) return null;
                  return (
                    <tr key={state}>
                      <th scope="row">{ELIGIBILITY_LABELS[state]}</th>
                      <td className={`${styles.numeric} gd-tabular`}>
                        {bar.min_qualified_n}건
                      </td>
                      <td className={`${styles.numeric} gd-tabular`}>
                        {Math.round(bar.min_verified_ratio * 100)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.h2}>지표는 살 수 없습니다</h2>
        <p className={styles.body}>
          기업의 후원, 페이지 소유권 확인, 광고 집행 여부는 기록의 가중치나 공개
          지표 계산에 어떤 영향도 주지 않습니다. 정정 요청은 사실관계를 다투는
          절차이며, 기록을 삭제할 권한을 부여하지 않습니다.
        </p>
      </section>
    </article>
  );
}
