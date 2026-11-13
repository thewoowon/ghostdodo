/**
 * Naming the visitor to the API.
 *
 * Production is Vercel -> Railway's edge -> API, and Railway's edge replaces
 * X-Forwarded-For with the address that connected to it — Vercel's. Measured
 * 2026-11-13: the API could not tell one visitor from another, so sign-in,
 * search, and evidence uploads shared one rate-limit bucket site-wide.
 *
 * So the web tier says who the visitor is, in a header the edge leaves alone,
 * and proves it is the one saying so with a secret shared with the API. The
 * Railway hostname is public; without the secret, the IP header would be
 * something any caller could type.
 *
 * Server-only: the secret is read from `PROXY_SHARED_SECRET`, which is not
 * `NEXT_PUBLIC_` and so never reaches a browser bundle.
 */
export const CLIENT_IP_HEADER = "X-GD-Client-IP";
export const PROXY_SECRET_HEADER = "X-GD-Proxy-Secret";

/**
 * The visitor's address as Vercel's edge recorded it. Vercel overwrites both
 * headers on the way in, so on Vercel neither is caller-supplied. Elsewhere
 * (`next start` locally) they may be absent or forged, which is why the
 * secret is set only on Vercel and the API ignores the header without it.
 */
export function visitorIp(headers: Headers): string | null {
  const real = headers.get("x-real-ip")?.trim();
  if (real) return real;
  const first = headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return first || null;
}

/**
 * Sets the vouching pair on an outgoing request. Always strips first, so a
 * browser can never smuggle its own pair through — with no secret
 * configured, the API simply receives neither header.
 */
export function vouchFor(
  headers: Headers,
  ip: string | null,
  secret: string | undefined = process.env.PROXY_SHARED_SECRET,
): void {
  headers.delete(CLIENT_IP_HEADER);
  headers.delete(PROXY_SECRET_HEADER);
  if (!secret || !ip) return;
  headers.set(CLIENT_IP_HEADER, ip);
  headers.set(PROXY_SECRET_HEADER, secret);
}
