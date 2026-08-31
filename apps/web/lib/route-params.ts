/**
 * Route parameter decoding.
 *
 * Next passes dynamic segment values percent-encoded, exactly as they appear
 * in the URL. Handing that straight to a fetch helper that encodes its inputs
 * produces a double-encoded path (`%25EA%25B7%25B8…`) and a 404 — a bug that
 * is invisible for ASCII slugs and breaks every Korean one, which is most of
 * them here.
 *
 * Decode once at the route boundary; everything downstream then works with
 * plain values and encodes on its way out.
 */
export function decodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    // Malformed escape sequence — use the raw value rather than throwing on
    // what is ultimately just a bad URL.
    return value;
  }
}
