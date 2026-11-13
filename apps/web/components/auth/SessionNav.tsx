"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getSession, signOut } from "@/lib/api/auth";
import type { SessionUser } from "@/lib/api/types";

import styles from "./SessionNav.module.css";

export type SessionState =
  | { status: "unknown" }
  | { status: "anonymous" }
  | { status: "signed-in"; user: SessionUser };

export type Session = { state: SessionState; leave: () => Promise<void> };

/**
 * Sign-in state for the header.
 *
 * Resolved in the browser rather than on the server on purpose: reading the
 * session during render would make every page in the app dynamic, and the
 * company pages are the SEO surface.
 *
 * A hook rather than a component so the header asks once and renders the
 * answer in two places — the inline row on wide screens and the menu panel
 * on phones — without a second `/auth/me` per navigation.
 */
export function useSession(): Session {
  const [state, setState] = useState<SessionState>({ status: "unknown" });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let cancelled = false;
    getSession()
      .then((user) => !cancelled && setState({ status: "signed-in", user }))
      // 401 is the ordinary answer for a signed-out visitor, not a failure.
      .catch(() => !cancelled && setState({ status: "anonymous" }));
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const leave = useCallback(async () => {
    try {
      await signOut();
    } catch {
      // The cookie may already be gone; either way stop showing an account.
    }
    setState({ status: "anonymous" });
    router.refresh();
  }, [router]);

  return { state, leave };
}

type Props = {
  session: Session;
  /** `inline` sits in the header row; `menu` is a stacked block in the
   *  phone menu, where every entry is a full-width tap target. */
  layout?: "inline" | "menu";
};

/** Until the answer arrives nothing is rendered, so the header never
 *  flashes "로그인" at someone who is signed in. */
export function SessionNav({ session, layout = "inline" }: Props) {
  const pathname = usePathname();
  const { state, leave } = session;
  const menu = layout === "menu";

  if (state.status === "unknown") {
    return <span className={menu ? styles.menuPlaceholder : styles.placeholder} aria-hidden />;
  }

  if (state.status === "anonymous") {
    return (
      <Link
        href={`/sign-in?next=${encodeURIComponent(pathname)}`}
        className={menu ? styles.menuItem : styles.signIn}
      >
        로그인
      </Link>
    );
  }

  if (menu) {
    return (
      <>
        <Link href="/me" className={styles.menuItem}>
          내 활동
          <span className={styles.menuHandle}>{state.user.handle}</span>
        </Link>
        <button type="button" onClick={leave} className={styles.menuItem}>
          로그아웃
        </button>
      </>
    );
  }

  return (
    <span className={styles.account}>
      <Link href="/me" className={styles.handle}>
        {state.user.handle}
      </Link>
      <button type="button" onClick={leave} className={styles.signOut}>
        로그아웃
      </button>
    </span>
  );
}
