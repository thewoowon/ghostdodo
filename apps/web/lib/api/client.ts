/**
 * Typed API client.
 *
 * Business logic lives in FastAPI; this is transport only (docs/04 §3). Two
 * base URLs exist on purpose: the browser talks to the public origin, while
 * Server Components may need an internal address inside a container network.
 */
import type { ApiErrorBody } from "./types";

const PUBLIC_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * In production the public base is the relative path `/api/v1`, which the
 * Vercel rewrite forwards. A relative URL is meaningless to `fetch` on the
 * server, so Server Components need an absolute one — and it may as well
 * skip the proxy hop and address the API directly.
 *
 * `API_ORIGIN` already has to exist for the rewrite, so it is reused here
 * rather than asking for the same host twice under two names.
 */
const INTERNAL_BASE = (() => {
  if (process.env.API_INTERNAL_BASE_URL) return process.env.API_INTERNAL_BASE_URL;
  if (PUBLIC_BASE.startsWith("/") && process.env.API_ORIGIN) {
    return `${process.env.API_ORIGIN}${PUBLIC_BASE}`;
  }
  return PUBLIC_BASE;
})();

function baseUrl(): string {
  if (typeof window !== "undefined") return PUBLIC_BASE;
  if (INTERNAL_BASE.startsWith("/")) {
    // Caught here rather than as fetch's opaque "Failed to parse URL".
    throw new Error(
      "Server-side API base is relative. Set API_ORIGIN (or API_INTERNAL_BASE_URL) " +
        "to the API's absolute origin.",
    );
  }
  return INTERNAL_BASE;
}

/**
 * The API origin as the browser must reach it.
 *
 * Needed for links the browser *navigates* to rather than fetches — the
 * Google sign-in hop leaves the app entirely, so it cannot go through
 * `apiRequest`, and it must never use the internal address.
 */
export function publicApiUrl(path: string): string {
  return `${PUBLIC_BASE}${path}`;
}

/** A failure the API described in its error envelope. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody["error"]) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.requestId = body.request_id;
    this.details = body.details;
  }
}

/** The API could not be reached at all — distinct from an API-level error. */
export class ApiUnavailableError extends Error {
  constructor(cause: unknown) {
    super("API에 연결할 수 없습니다.");
    this.name = "ApiUnavailableError";
    this.cause = cause;
  }
}

export type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Forwarded cookies for Server Component reads of authenticated routes. */
  cookie?: string;
  idempotencyKey?: string;
  /** Next.js cache directives. Public company data is tagged for revalidation. */
  next?: { revalidate?: number | false; tags?: string[] };
  cache?: RequestCache;
  signal?: AbortSignal;
  /** Lets the request outlive the page that started it — required for a
   *  click that is recorded as the browser navigates away. */
  keepalive?: boolean;
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    cookie,
    idempotencyKey,
    next,
    cache,
    signal,
    keepalive,
  } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (cookie) headers["Cookie"] = cookie;
  if (idempotencyKey) headers["X-Idempotency-Key"] = idempotencyKey;

  // Resolved outside the try: a misconfigured base is a deployment error,
  // not an unreachable API, and must not be reported as one.
  const url = `${baseUrl()}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      // Session cookie must ride along on browser mutations.
      credentials: "include",
      ...(next ? { next } : {}),
      ...(cache ? { cache } : {}),
      ...(signal ? { signal } : {}),
      ...(keepalive ? { keepalive } : {}),
    });
  } catch (cause) {
    throw new ApiUnavailableError(cause);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (
      payload &&
      typeof payload === "object" &&
      "error" in payload &&
      payload.error
    ) {
      throw new ApiError(response.status, (payload as ApiErrorBody).error);
    }
    throw new ApiError(response.status, {
      code: "UNKNOWN_ERROR",
      message: "요청을 처리하지 못했습니다.",
      request_id: response.headers.get("X-Request-ID") ?? "-",
      details: {},
    });
  }

  return payload as T;
}

/** Cache tag for one company's public data, so a verification can bust it. */
export function companyTag(slug: string): string {
  return `company:${slug}`;
}
