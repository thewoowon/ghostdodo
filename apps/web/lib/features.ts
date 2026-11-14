/**
 * Web-side switches for surfaces the API can close.
 *
 * Read through functions rather than module constants so tests can flip
 * them; Next still inlines `NEXT_PUBLIC_*` at each access site at build.
 */

/**
 * Jobs are closed in production (`ENABLE_JOBS=false` on the API, since
 * 2026-11-14): the only postings were demo fixtures linking to example.com,
 * which read as real next to 72k real companies. Off unless set, so the
 * production build needs no Vercel change; set `NEXT_PUBLIC_ENABLE_JOBS=true`
 * alongside the API flag to bring the menu entry back.
 */
export function jobsEnabled(): boolean {
  return process.env.NEXT_PUBLIC_ENABLE_JOBS === "true";
}
