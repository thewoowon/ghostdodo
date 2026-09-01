import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque } from "next/font/google";

import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";

import "@/styles/globals.css";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

/**
 * Display face for the wordmark only — body and UI text stay on Pretendard,
 * which carries the Korean. Exposed as a CSS variable rather than a class so
 * nothing inherits it by accident; `Wordmark` is the sole consumer.
 *
 * Variable font, so no `weight` list: the wordmark needs 400 and 800 and gets
 * the whole range for one file. `next/font` self-hosts this at build time —
 * the build fetches from Google once, so a fully offline build needs the
 * Next font cache warm.
 */
const wordmark = Bricolage_Grotesque({
  subsets: ["latin"],
  display: "swap",
  variable: "--gd-font-wordmark",
});

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: {
    default: "GhostDodo — 지원하기 전에, 답은 해주는 회사인지 확인하세요",
    template: "%s | GhostDodo",
  },
  description:
    "지원자들이 직접 남긴 채용 응답 기록을 바탕으로 회사별 결과 통보율과 응답 시간을 확인하세요.",
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: "GhostDodo",
    url: APP_URL,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf8f5" },
    { media: "(prefers-color-scheme: dark)", color: "#14120f" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" className={wordmark.variable}>
      <body>
        <a href="#main" className="gd-sr-only">
          본문으로 건너뛰기
        </a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
