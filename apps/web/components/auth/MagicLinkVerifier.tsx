"use client";

import type { Route } from "next";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { DodoEgg } from "@/components/brand/svg/marks";
import { ApiError, ApiUnavailableError } from "@/lib/api/client";
import { verifyMagicLink } from "@/lib/api/auth";

import styles from "./MagicLinkVerifier.module.css";

const NO_TOKEN = "로그인 링크가 올바르지 않습니다.";

export function MagicLinkVerifier({ token, next }: { token: string | null; next: string }) {
  const router = useRouter();
  const [failure, setFailure] = useState<string | null>(null);
  // A magic link is single-use, and React strict mode mounts effects twice
  // in development — burning the token on the first run and reporting
  // "already used" on the second.
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;

    verifyMagicLink(token)
      .then(() => {
        // `typedRoutes` cannot know a runtime string is a real route. This
        // one was reduced to a same-site path at the route boundary.
        router.replace(next as Route);
        router.refresh();
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError) {
          setFailure(error.message);
        } else if (error instanceof ApiUnavailableError) {
          setFailure("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
        } else {
          setFailure("로그인을 완료하지 못했습니다.");
        }
      });
  }, [token, next, router]);

  // A missing token is knowable at render time; deriving it here keeps the
  // effect to the one job that genuinely needs one.
  const message = token === null ? NO_TOKEN : failure;

  if (message === null) {
    return (
      <p className={styles.working} role="status">
        로그인 중입니다…
      </p>
    );
  }

  return (
    <>
      <DodoEgg size={34} className={styles.mark} />
      <h1 className={styles.title}>로그인하지 못했습니다</h1>
      <p className={styles.body}>{message}</p>
      <Link href={`/sign-in?next=${encodeURIComponent(next)}`} className={styles.link}>
        다시 로그인하기
      </Link>
    </>
  );
}
