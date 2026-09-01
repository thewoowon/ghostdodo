import Link from "next/link";

import { ApplyButton } from "@/components/jobs/ApplyButton";
import { DodoEgg, FieldNotebook } from "@/components/brand/svg/marks";
import type { JobCard } from "@/lib/api/types";
import { jobClosing, jobFacets, sourceName } from "@/lib/format/jobs";

import styles from "./JobCardList.module.css";

type Props = {
  jobs: JobCard[];
  /** Suppressed on a company's own jobs tab, where it would repeat. */
  showCompany?: boolean;
  emptyBody?: string;
};

/**
 * Linked postings.
 *
 * Every card names the source it came from — GhostDodo did not write the
 * posting and must not look like it did (docs/09 Phase 6 acceptance) — and
 * carries no response rate, because a posting is not an observation.
 */
export function JobCardList({ jobs, showCompany = true, emptyBody }: Props) {
  if (jobs.length === 0) {
    return (
      <div className={styles.empty}>
        <DodoEgg size={30} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>지금 연결된 공고가 없습니다</p>
        <p className={styles.emptyBody}>
          {emptyBody ?? "새 공고가 확인되면 이곳에 표시됩니다."}
        </p>
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {jobs.map((job) => {
        const closing = jobClosing(job);
        const facets = jobFacets(job);

        return (
          <li key={job.id} className={styles.card}>
            <div className={styles.head}>
              <span className={styles.source}>
                <FieldNotebook size={14} />
                {sourceName(job)}
              </span>
              <span className={`${styles.closing} ${styles[closing.kind]}`}>
                {closing.label}
              </span>
            </div>

            <h3 className={styles.title}>
              <Link href={`/jobs/${job.id}`} className={styles.titleLink}>
                {job.title}
              </Link>
            </h3>

            {showCompany && (
              <p className={styles.company}>
                <Link
                  href={`/companies/${job.company.slug}`}
                  className={styles.companyLink}
                >
                  {job.company.display_name_ko}
                </Link>
                {job.company.is_demo && (
                  <span className={styles.demoTag}>샘플 데이터</span>
                )}
              </p>
            )}

            {facets.length > 0 && (
              <ul className={styles.facets}>
                {facets.map((facet) => (
                  <li key={facet} className={styles.facet}>
                    {facet}
                  </li>
                ))}
              </ul>
            )}

            <div className={styles.actions}>
              <ApplyButton
                jobId={job.id}
                applyUrl={job.apply_url}
                isOpen={job.is_open}
                variant="compact"
              />
              <Link href={`/jobs/${job.id}`} className={styles.detailLink}>
                공고 자세히
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
