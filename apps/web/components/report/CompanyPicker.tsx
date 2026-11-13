"use client";

import { useEffect, useState } from "react";

import { CompanyRequestForm } from "@/components/company/CompanyRequestForm";
import { searchCompanies } from "@/lib/api/queries";
import type { CompanySummary } from "@/lib/api/types";

import styles from "./CompanyPicker.module.css";

/** Company selection inside the wizard. Selecting is required — a report
 *  cannot be attached to a free-typed company name. */
export function CompanyPicker({
  value,
  onSelect,
}: {
  value: string;
  onSelect: (company: CompanySummary) => void;
}) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<CompanySummary[]>([]);
  const [selected, setSelected] = useState<string | null>(value || null);

  useEffect(() => {
    const trimmed = query.trim();
    // Nothing to fetch. Emptiness is derived in `visibleResults` rather than
    // written back as state from inside the effect.
    if (!trimmed || trimmed === selected) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      searchCompanies(trimmed, { signal: controller.signal })
        .then(setResults)
        .catch(() => setResults([]));
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, selected]);

  const trimmed = query.trim();
  const visibleResults = !trimmed || trimmed === selected ? [] : results;

  return (
    <div className={styles.wrap}>
      <input
        className={styles.input}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setSelected(null);
        }}
        placeholder="회사 이름을 검색하세요"
        aria-label="회사 검색"
        autoComplete="off"
      />

      {visibleResults.length > 0 && (
        <ul className={styles.list}>
          {visibleResults.map((company) => (
            <li key={company.id}>
              <button
                type="button"
                className={styles.option}
                onClick={() => {
                  onSelect(company);
                  setQuery(company.display_name_ko);
                  setSelected(company.display_name_ko);
                  setResults([]);
                }}
              >
                <span className={styles.name}>{company.display_name_ko}</span>
                <span className={styles.meta}>
                  {company.industry ?? "업종 미상"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected && <p className={styles.selected}>선택됨: {selected}</p>}

      {!selected && trimmed.length > 1 && visibleResults.length === 0 && (
        <div className={styles.missing}>
          <p>
            찾는 회사가 없다면 등록을 요청할 수 있습니다. 검토 후 도감에
            추가되면 이어서 기록할 수 있습니다.
          </p>
          {/* Keyed on the query so a fresh search starts a fresh form. */}
          <CompanyRequestForm key={trimmed} initialName={trimmed} />
        </div>
      )}
    </div>
  );
}
