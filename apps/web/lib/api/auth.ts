/**
 * Sign-in.
 *
 * Two providers, one account: Google and the original email magic link both
 * resolve to the same user row on a verified address, so a contributor who
 * switches keeps their reports and reputation.
 *
 * Everything here runs in the browser on purpose. The session is an httpOnly
 * cookie the API sets on its own response, so a fetch made from the Next
 * server would attach the cookie to the wrong client — the sign-in calls have
 * to be made by the browser itself.
 */
import { apiRequest, publicApiUrl } from "./client";
import type { SessionUser, SignInAccepted } from "./types";

/**
 * Where to send the browser for Google sign-in.
 *
 * A full navigation, not a fetch: the flow leaves the app for Google and
 * comes back to the API's callback, which sets the session cookie and
 * redirects onward. `next` is where to land afterwards, and the API reduces
 * it to a same-site path before trusting it.
 */
export function googleSignInUrl(next?: string): string {
  const params = next ? `?${new URLSearchParams({ next })}` : "";
  return publicApiUrl(`/auth/google/start${params}`);
}

export function requestMagicLink(email: string): Promise<SignInAccepted> {
  return apiRequest<SignInAccepted>("/auth/sign-in", {
    method: "POST",
    body: { email },
  });
}

export function verifyMagicLink(token: string): Promise<SessionUser> {
  return apiRequest<SessionUser>("/auth/verify", {
    method: "POST",
    body: { token },
  });
}

export function getSession(): Promise<SessionUser> {
  return apiRequest<SessionUser>("/auth/me", { cache: "no-store" });
}

export function signOut(): Promise<void> {
  return apiRequest<void>("/auth/sign-out", { method: "POST" });
}
