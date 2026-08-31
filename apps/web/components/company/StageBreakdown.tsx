import type { StageMetrics } from "@/lib/api/types";
import { STAGE_LABELS } from "@/lib/domain";
import { formatDays, formatRate } from "@/lib/format/metrics";

import styles from "./StageBreakdown.module.css";

/**
 * Where in the funnel communication stops.
 *
 * Rates here are suppressed by the same rule as the headline metrics: when
 * the API returns null, the row shows the observation count only.
 */
export function StageBreakdown({ stages }: { stages: StageMetrics[] }) {
  if (stages.length === 0) {
    return (
      <p className={styles.empty}>
        아직 단계별로 나눌 만큼의 기록이 없습니다.
      </p>
    );
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption className="gd-sr-only">
          채용 단계별 결과 통보율과 응답 소요 시간
        </caption>
        <thead>
          <tr>
            <th scope="col">단계</th>
            <th scope="col" className={styles.numeric}>기록</th>
            <th scope="col" className={styles.numeric}>결과 통보율</th>
            <th scope="col" className={styles.numeric}>응답 소요</th>
          </tr>
        </thead>
        <tbody>
          {stages.map((stage) => {
            const rate = formatRate(stage.response_rate);
            return (
              <tr key={stage.stage}>
                <th scope="row" className={styles.stageName}>
                  {STAGE_LABELS[stage.stage]}
                </th>
                <td className={`${styles.numeric} gd-tabular`}>
                  {stage.qualified_n}
                </td>
                <td className={`${styles.numeric} gd-tabular`}>
                  {rate === null ? (
                    <span className={styles.suppressed}>표본 부족</span>
                  ) : (
                    <span className={styles.bar}>
                      <span
                        className={styles.barFill}
                        style={{ width: `${(stage.response_rate ?? 0) * 100}%` }}
                        aria-hidden
                      />
                      <span className={styles.barValue}>{rate}</span>
                    </span>
                  )}
                </td>
                <td className={`${styles.numeric} gd-tabular`}>
                  {formatDays(stage.median_response_days) ?? "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
