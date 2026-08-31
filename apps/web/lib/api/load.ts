/**
 * Resolving an API call to a value a Server Component can render.
 *
 * JSX must not be constructed inside a try/catch: React renders lazily, so an
 * error thrown during render escapes the handler anyway, and the catch gives
 * a false sense of coverage. Fetch inside the try, resolve the outcome to a
 * plain value, and branch on it outside.
 */
import { ApiError, ApiUnavailableError } from "./client";

export type LoadFailure = "unauthenticated" | "forbidden" | "not-found" | "unavailable";

export type LoadResult<T> =
  | { ok: true; data: T }
  | { ok: false; failure: LoadFailure };

export async function load<T>(fetcher: () => Promise<T>): Promise<LoadResult<T>> {
  try {
    return { ok: true, data: await fetcher() };
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) return { ok: false, failure: "unauthenticated" };
      if (error.status === 403) return { ok: false, failure: "forbidden" };
      if (error.status === 404) return { ok: false, failure: "not-found" };
    }
    if (error instanceof ApiUnavailableError) {
      return { ok: false, failure: "unavailable" };
    }
    // Anything unexpected is a real bug — let it reach the error boundary
    // rather than being flattened into a friendly message.
    throw error;
  }
}
