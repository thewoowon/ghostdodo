"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { DodoMark } from "@/components/brand/svg/DodoMark";
import { searchCompanies } from "@/lib/api/queries";
import type { CompanySummary } from "@/lib/api/types";

import styles from "./CompanySearch.module.css";

const DEBOUNCE_MS = 180;

type Props = {
  size?: "hero" | "compact";
  initialQuery?: string;
  autoFocus?: boolean;
};

/**
 * Company autocomplete — the landing page's visual anchor (docs/03 §2).
 *
 * Fully keyboard navigable per the ARIA combobox pattern: arrows move the
 * active option, Enter opens it, Escape closes the list.
 */
export function CompanySearch({
  size = "hero",
  initialQuery = "",
  autoFocus = false,
}: Props) {
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<CompanySummary[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const trimmed = query.trim();
    // An empty query is a derived state, not a stored one — clearing results
    // here would set state synchronously inside an effect and cascade a
    // render. See `visibleResults` below.
    if (trimmed.length === 0) return;

    // Abort in-flight requests so a fast typist never sees an older response
    // overwrite a newer one.
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setStatus("loading");
      searchCompanies(trimmed, controller.signal)
        .then((items) => {
          setResults(items);
          setActiveIndex(-1);
          setOpen(true);
          setStatus("idle");
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") return;
          setStatus("error");
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  function goTo(company: CompanySummary) {
    setOpen(false);
    router.push(`/companies/${company.slug}`);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (visibleResults.length === 0) return;
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      setOpen(true);
      setActiveIndex((current) => {
        const next = current + delta;
        if (next < 0) return visibleResults.length - 1;
        if (next >= visibleResults.length) return 0;
        return next;
      });
      return;
    }
    if (event.key === "Enter") {
      const active = activeIndex >= 0 ? visibleResults[activeIndex] : undefined;
      event.preventDefault();
      if (active) {
        goTo(active);
      } else if (query.trim()) {
        router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      }
    }
  }

  const hasQuery = query.trim().length > 0;
  // Results belong to the last non-empty query; clearing the box hides them
  // without a state write.
  const visibleResults = hasQuery ? results : [];
  const showEmpty =
    open && hasQuery && status === "idle" && visibleResults.length === 0;

  return (
    <div
      ref={rootRef}
      className={`${styles.root} ${size === "hero" ? styles.hero : styles.compact}`}
    >
      <div className={styles.field}>
        <DodoMark size={size === "hero" ? 28 : 22} className={styles.mark} />
        <input
          type="search"
          role="combobox"
          className={styles.input}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => visibleResults.length > 0 && setOpen(true)}
          placeholder="회사 이름을 검색하세요"
          aria-label="회사 검색"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined
          }
          autoComplete="off"
          // Search is the page's primary action, so focusing it on the
          // dedicated search page is what a visitor expects.
          autoFocus={autoFocus}
        />
      </div>

      {open && (visibleResults.length > 0 || showEmpty) && (
        <ul className={styles.list} id={listId} role="listbox" aria-label="검색 결과">
          {visibleResults.map((company, index) => (
            <li key={company.id}>
              <button
                type="button"
                id={`${listId}-option-${index}`}
                role="option"
                aria-selected={index === activeIndex}
                className={`${styles.option} ${
                  index === activeIndex ? styles.optionActive : ""
                }`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => goTo(company)}
              >
                {/* Neutral monogram fallback — no scraped logos. */}
                <span className={styles.monogram} aria-hidden>
                  {company.display_name_ko.slice(0, 1)}
                </span>
                <span className={styles.optionBody}>
                  <span className={styles.optionName}>
                    {company.display_name_ko}
                    {company.is_demo && <span className={styles.demo}>샘플</span>}
                  </span>
                  <span className={styles.optionMeta}>
                    {company.industry ?? "업종 미상"}
                    {company.name_en ? ` · ${company.name_en}` : ""}
                    {` · 기록 ${company.public_report_count}건`}
                  </span>
                </span>
              </button>
            </li>
          ))}

          {showEmpty && (
            <li className={styles.empty}>
              <p className={styles.emptyTitle}>아직 도감에 없는 회사입니다.</p>
              <p className={styles.emptyBody}>
                새로운 흔적을 발견하셨나요? 회사를 등록 요청할 수 있습니다.
              </p>
            </li>
          )}
        </ul>
      )}

      {status === "error" && (
        <p className={styles.error} role="status">
          검색을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
        </p>
      )}
    </div>
  );
}
