"use client";

import Link from "next/link";
import { useState } from "react";

import { GoogleGlyph } from "@/components/auth/GoogleGlyph";
import { ApiError, ApiUnavailableError } from "@/lib/api/client";
import { googleSignInUrl, requestMagicLink } from "@/lib/api/auth";

import styles from "./SignInPanel.module.css";

/** Reasons the API can bounce someone back here from the Google callback. */
const CALLBACK_ERRORS: Record<string, string> = {
  state: "로그인 요청이 만료되었습니다. 다시 시도해 주세요.",
  cancelled: "구글 로그인이 취소되었습니다.",
  google: "구글 로그인을 완료하지 못했습니다. 다시 시도해 주세요.",
  deactivated: "비활성화된 계정입니다.",
};

type Props = {
  /** Same-site path to land on after signing in. */
  next: string;
  callbackError: string | null;
  /** Resolved on the server before first paint. Asking from the browser
   *  rendered the button and then withdrew it once the answer came back,
   *  which reads as broken — and with Google off, it always came back. */
  googleEnabled: boolean;
};

export function SignInPanel({ next, callbackError, googleEnabled }: Props) {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(
    callbackError ? (CALLBACK_ERRORS[callbackError] ?? CALLBACK_ERRORS.google!) : null,
  );

  async function sendLink(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const accepted = await requestMagicLink(email.trim());
      setSent(true);
      setDevToken(accepted.dev_token);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.code === "RATE_LIMITED"
            ? "로그인 요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."
            : err.message,
        );
      } else if (err instanceof ApiUnavailableError) {
        setError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      } else {
        setError("로그인 링크를 보내지 못했습니다.");
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={styles.panel}>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {googleEnabled && (
        <>
          <a href={googleSignInUrl(next)} className={styles.google}>
            <GoogleGlyph size={18} />
            구글 계정으로 계속하기
          </a>
          <p className={styles.divider}>
            <span>또는</span>
          </p>
        </>
      )}

      {sent ? (
        <div className={styles.sent} role="status">
          <p className={styles.sentTitle}>{email}로 로그인 링크를 보냈습니다.</p>
          <p className={styles.sentBody}>
            링크는 15분간 유효하고 한 번만 사용할 수 있습니다.
          </p>
          {devToken && (
            // Development only: the API returns the token so a local setup
            // needs no mail server. Never populated in production.
            <Link
              href={`/auth/verify?token=${encodeURIComponent(devToken)}&next=${encodeURIComponent(next)}`}
              className={styles.devLink}
            >
              개발 환경: 바로 로그인하기
            </Link>
          )}
        </div>
      ) : (
        <form className={styles.form} onSubmit={sendLink}>
          <label className={styles.label} htmlFor="sign-in-email">
            이메일로 로그인
          </label>
          <div className={styles.emailRow}>
            <input
              id="sign-in-email"
              type="email"
              required
              autoComplete="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
            <button type="submit" className={styles.submit} disabled={sending}>
              {sending ? "보내는 중…" : "링크 받기"}
            </button>
          </div>
          <p className={styles.hint}>
            비밀번호는 없습니다. 처음 로그인하면 계정이 자동으로 만들어지고,
            공개되는 이름은 임의로 생성된 별명입니다.
          </p>
        </form>
      )}
    </div>
  );
}
