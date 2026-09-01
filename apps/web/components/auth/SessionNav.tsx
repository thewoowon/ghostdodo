"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getSession, signOut } from "@/lib/api/auth";
import type { SessionUser } from "@/lib/api/types";

import styles from "./SessionNav.module.css";

type State =
  | { status: "unknown" }
  | { status: "anonymous" }
  | { status: "signed-in"; user: SessionUser };

/**
 * Sign-in state in the header.
 *
 * Resolved in the browser rather than on the server on purpose: reading the
 * session during render would make every page in the app dynamic, and the
 * company pages are the SEO surface. Until the answer arrives nothing is
 * rendered, so the header never flashes "로그인" at someone who is.
 */
export function SessionNav() {
  const [state, setState] = useState<State>({ status: "unknown" });
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

  if (state.status === "unknown") {
    return <span className={styles.placeholder} aria-hidden />;
  }

  if (state.status === "anonymous") {
    return (
      <Link
        href={`/sign-in?next=${encodeURIComponent(pathname)}`}
        className={styles.signIn}
      >
        로그인
      </Link>
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
