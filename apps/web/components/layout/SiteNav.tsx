"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { SessionNav, useSession } from "@/components/auth/SessionNav";
import { jobsEnabled } from "@/lib/features";

import styles from "./SiteNav.module.css";

type NavLink = { href: "/jobs" | "/dex" | "/methodology"; label: string };

function navLinks(): NavLink[] {
  return [
    ...(jobsEnabled() ? [{ href: "/jobs" as const, label: "채용공고" }] : []),
    { href: "/dex", label: "도감" },
    { href: "/methodology", label: "측정 기준" },
  ];
}

/**
 * Primary navigation.
 *
 * Wide screens get one row. On phones the row does not fit — it pushed the
 * layout viewport to ~470px and the browser zoomed every page out — so the
 * links fold into a disclosure panel and only `기록하기` stays in the bar,
 * because recording is the one action the product exists to collect.
 *
 * Both layouts are in the DOM and CSS picks one, so there is no width
 * measurement in JS and no flash of the wrong layout on first paint.
 */
export function SiteNav() {
  const links = navLinks();
  const session = useSession();
  const pathname = usePathname();
  // The menu remembers the page it was opened on, so navigating — the usual
  // way out of it — closes it without an effect to reset state.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  const close = useCallback((returnFocus: boolean) => {
    setOpenOn(null);
    if (returnFocus) toggleRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close(true);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  return (
    <nav className={styles.nav} aria-label="주요 메뉴">
      <div className={styles.inline}>
        {links.map((link) => (
          <Link key={link.href} href={link.href} className={styles.navLink}>
            {link.label}
          </Link>
        ))}
        <SessionNav session={session} />
      </div>

      <Link href="/report/new" className={styles.cta}>
        기록하기
      </Link>

      <button
        ref={toggleRef}
        type="button"
        className={styles.toggle}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
        onClick={() => setOpenOn(open ? null : pathname)}
      >
        <MenuGlyph open={open} />
      </button>

      <div
        id={panelId}
        className={styles.panel}
        hidden={!open}
        // A link to the page already open changes no pathname, so close on
        // the click itself rather than waiting for the route effect.
        onClick={(event) => {
          if ((event.target as HTMLElement).closest("a")) close(false);
        }}
      >
        <div className={`gd-shell ${styles.panelBody}`}>
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={styles.menuLink}
              aria-current={pathname === link.href ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
          <hr className={styles.rule} />
          <SessionNav session={session} layout="menu" />
        </div>
      </div>
      {open && <div className={styles.scrim} aria-hidden onClick={() => close(false)} />}
    </nav>
  );
}

/** Three rules that close into a cross. Drawn here, not an emoji or a font
 *  glyph (docs/02 §3). */
function MenuGlyph({ open }: { open: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      {open ? (
        <path
          d="M6 6l12 12M18 6L6 18"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      ) : (
        <path
          d="M4 7h16M4 12h16M4 17h16"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
