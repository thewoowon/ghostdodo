import Link from "next/link";

import { DodoEgg } from "@/components/brand/svg/marks";
import { CompanyRequestForm } from "@/components/company/CompanyRequestForm";
import type { CompanySummary } from "@/lib/api/types";

import styles from "./CompanyResultList.module.css";

export function CompanyResultList({
  companies,
  query,
}: {
  companies: CompanySummary[];
  query: string;
}) {
  if (companies.length === 0) {
    return (
      <div className={styles.empty}>
        <DodoEgg size={32} className={styles.emptyMark} />
        <p className={styles.emptyTitle}>
          &lsquo;{query}&rsquo; 와 일치하는 회사를 찾지 못했습니다
        </p>
        <p className={styles.emptyBody}>
          아직 도감에 없는 회사일 수 있습니다. 등록을 요청하면 검토 후
          추가됩니다.
        </p>
        <CompanyRequestForm initialName={query} />
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {companies.map((company) => (
        <li key={company.id}>
          <Link href={`/companies/${company.slug}`} className={styles.row}>
            <span className={styles.monogram} aria-hidden>
              {company.display_name_ko.slice(0, 1)}
            </span>
            <span className={styles.body}>
              <span className={styles.name}>
                {company.display_name_ko}
                {company.is_demo && <span className={styles.demo}>샘플</span>}
              </span>
              <span className={styles.meta}>
                {company.industry ?? "업종 미상"}
                {company.name_en ? ` · ${company.name_en}` : ""}
              </span>
            </span>
            {/* Report count is a volume figure, never presented as a rate.
                A held-back company shows none: even a count says how much
                has been filed about it. */}
            {company.published && (
              <span className={`${styles.count} gd-tabular`}>
                기록 {company.public_report_count}건
              </span>
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}
