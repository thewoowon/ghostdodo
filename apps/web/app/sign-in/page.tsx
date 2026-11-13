import type { Metadata } from "next";

import { SignInPanel } from "@/components/auth/SignInPanel";
import { DodoMark } from "@/components/brand/svg/DodoMark";
import { getAuthProviders } from "@/lib/api/queries";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "로그인",
  description: "GhostDodo에 기록을 남기려면 로그인하세요.",
  // A sign-in page has nothing to rank for, and indexing it invites
  // credential-phishing lookalikes into search results.
  robots: { index: false, follow: false },
};

type Props = {
  searchParams: Promise<{ next?: string; error?: string }>;
};

/** Same-site paths only — this value ends up in a redirect. */
function safeNext(raw: string | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}

/**
 * Whether to offer Google. Any failure is a no: the email path always works,
 * so a sign-in page that cannot reach the API still shows a working door
 * rather than an error page. Resolved to a boolean here so no JSX is built
 * inside the try (see `lib/api/load.ts`).
 */
async function googleAvailable(): Promise<boolean> {
  try {
    return (await getAuthProviders()).google;
  } catch {
    return false;
  }
}

export default async function SignInPage({ searchParams }: Props) {
  const [{ next, error }, googleEnabled] = await Promise.all([
    searchParams,
    googleAvailable(),
  ]);

  return (
    <div className={`gd-shell ${styles.page}`}>
      <header className={styles.header}>
        <DodoMark size={44} className={styles.mark} />
        <h1 className={styles.title}>로그인</h1>
        <p className={styles.lede}>
          기록을 남기고 검토 결과를 확인하려면 로그인이 필요합니다. 회사
          페이지와 지표는 로그인 없이도 볼 수 있습니다.
        </p>
      </header>

      <SignInPanel
        next={safeNext(next)}
        callbackError={error ?? null}
        googleEnabled={googleEnabled}
      />

      <p className={styles.privacy}>
        로그인에 사용한 이메일은 계정 확인과 검토 결과 안내에만 씁니다.
        공개되는 이름은 임의로 생성된 별명이며, 작성자의 신원은 회사에도
        공개되지 않습니다.
      </p>
    </div>
  );
}
