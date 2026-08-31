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
const INTERNAL_BASE = process.env.API_INTERNAL_BASE_URL ?? PUBLIC_BASE;

function baseUrl(): string {
  return typeof window === "undefined" ? INTERNAL_BASE : PUBLIC_BASE;
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
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, cookie, idempotencyKey, next, cache, signal } =
    options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (cookie) headers["Cookie"] = cookie;
  if (idempotencyKey) headers["X-Idempotency-Key"] = idempotencyKey;

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      // Session cookie must ride along on browser mutations.
      credentials: "include",
      ...(next ? { next } : {}),
      ...(cache ? { cache } : {}),
      ...(signal ? { signal } : {}),
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
