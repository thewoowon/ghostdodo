import type { Metadata } from "next";

import { MagicLinkVerifier } from "@/components/auth/MagicLinkVerifier";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "로그인 확인",
  robots: { index: false, follow: false },
};

type Props = {
  searchParams: Promise<{ token?: string; next?: string }>;
};

function safeNext(raw: string | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}

/**
 * Where a magic link lands.
 *
 * `auth/service.py` builds the emailed link as `{web_base_url}/auth/verify`,
 * so this route's path is part of the API's contract — renaming it silently
 * breaks every link already in someone's inbox.
 *
 * The token is exchanged from the browser, not here: the session is an
 * httpOnly cookie the API sets on its response, and a fetch made by the Next
 * server would hand that cookie to the server instead of the person.
 */
export default async function VerifyPage({ searchParams }: Props) {
  const { token, next } = await searchParams;

  return (
    <div className={`gd-shell ${styles.page}`}>
      <MagicLinkVerifier token={token ?? null} next={safeNext(next)} />
    </div>
  );
}
