# GhostDodo — working notes

Read `README.md` first for what the product is and how to run it. This file
covers what you cannot infer from the code: the rules that must not be broken,
and the traps that have already cost time once.

The product handoff lives in `docs/handoff/` and is the source of record for
product rules. When code and handoff disagree, the handoff wins.

---

## Three rules that are not negotiable

These are enforced in code and covered by tests. If a change makes one of them
untrue, the change is wrong, not the rule.

1. **A rate the sample cannot support is never published.** Below the
   methodology bar the API returns `null` for every rate — not a small number —
   and the UI renders `표본 부족`. `formatRate` returns `null` rather than a
   string specifically so the type system forces callers to handle it.
2. **A rejection email is a successful response.** Response Rate measures
   explicit disposition, not good news. Reputation awards are identical
   whether a report says the company answered or went silent — nothing in the
   award table keys on negativity.
3. **Thresholds are configuration, never literals.** Every observation window,
   grace period, and sample bar lives in `apps/api/app/core/methodology.py`
   under a version id. Service code has no numeric literals for these. The
   public `/methodology` page renders from that same source, so the page and
   the numbers cannot drift.

Also load-bearing: **evidence is private** (signed URLs only, every moderator
view audit-logged before the URL is minted), and **reporter identity is never
exposed** — not publicly, and not to a company during a correction. A test
asserts the reporter id appears nowhere in the correction flow.

Directory imports establish that a company *exists*. Only qualified applicant
reports establish how it *behaves*. `TestImportCreatesNoMetrics` guards it.
The same rule covers job postings — a posting says a company is hiring and
nothing more (`TestPostingsCreateNoMetrics`).

**Standing is never awarded for what a report said.** This governs the
award table, the rank thresholds, *and* the badge rules in
`reputation/badges.py` — a badge keyed on silence found or companies accused
would reintroduce the asymmetry through a side door. `TestBadgeRulesReward
ContributionNotNegativity` guards it, and there is deliberately no streak
badge (docs/07 §4 warns about dark patterns in the same line it suggests one).

**Two sign-in providers, one account.** Google and the magic link both
resolve to one `users` row. Google matches `google_sub` first and verified
email second — never email alone, and never an unverified one. A change that
lets an unverified address reach `sign_in_with_google` is an account-takeover
bug, not a validation nit.

**Counting an apply click must never block the apply.** `지원하러 가기` is a
real anchor to the employer; the outbound-click POST rides alongside the
navigation and its failure is swallowed. Never convert it into a redirect
through the API or an `await` in front of the link.

---

## Traps that have already bitten

Each of these was a real bug. They are cheap to reintroduce.

**Postgres enums store values, not names.** Use `domain_enum()` from
`app/db/base.py`, which sets `values_callable`. Without it SQLAlchemy sends
`W6M` where the type holds `6m` — silently fine for every enum whose name
equals its value, and a runtime error for the ones where it does not.

**Ledger timestamps use `clock_timestamp()`, not `now()`.** `now()` returns the
transaction start time, so several ledger rows written in one transaction share
a timestamp and the append-only history cannot be ordered. Applies to
`reputation_events`, `credit_ledger`, `audit_logs`, `verification_reviews`, and
`evidence_access_logs`.

**Alembic must not re-create enum types.** They are created once in
`0001_bootstrap`. `env.py` has a `render_item` hook that renders them as
references; keep it when touching migrations.

**Next passes dynamic route params percent-encoded, but query params decoded.**
Use `decodeRouteParam()` at the route boundary. Encoding an already-encoded
slug yields `%25EA%25…` and a 404 — invisible for ASCII slugs, broken for every
Korean one.

**`pnpm typecheck` must run `next typegen` first.** Route types are generated,
not checked in. Without them `tsc` runs with no route union and `typedRoutes`
validates nothing, silently disabling the check that catches links to pages
that do not exist.

**Never construct JSX inside try/catch.** React renders lazily, so a
render-time error escapes the handler anyway. Use `load()` from
`apps/web/lib/api/load.ts`, which resolves a fetch to a discriminated result;
branch on it outside the try.

**Sessions have `autoflush=False`.** Loops that insert and then query for what
they just inserted must `flush()` explicitly. This is why
`directory.upsert_record` flushes on create — registries list one employer many
times, so intra-batch duplicates are the common case, not an edge case.

**pnpm 11 reads the native-build allowlist from `allowBuilds:` in
`pnpm-workspace.yaml`**, not from `.npmrc` or `package.json`.

**A stored URL reaching an `href` needs its scheme checked.** Posting URLs
come from importers and moderators, not from the renderer. `safe_apply_url()`
returns None for anything but http(s), and the client renders no CTA rather
than a `javascript:` link.

**`dev_token` is development and test only** (`settings.expose_dev_tokens`).
It hands back a working sign-in for any address typed, so gating it on
`is_production` — as it once was — left staging with an authentication
bypass. `check_production_hardening` refuses to boot if it is ever widened.

**Feature flags are read once, at import.** `--reload` does not watch `.env`,
so flipping `ENABLE_JOBS` needs an actual API restart, not a code edit.

**The session cookie is set by the API's origin, and the web app reads it
because cookies ignore ports.** That is why `localhost:3000` sees a cookie
from `localhost:8000`. It will NOT hold across different hosts in production
— api.example.com cannot set a host-only cookie the www origin can read.

**Sign-in calls must be made by the browser, never by a Server Component.**
The session arrives as `Set-Cookie` on the API's response; a fetch issued
from the Next server would attach it to the server. `/auth/verify` is a
client component for exactly this reason, and its path is part of the API's
contract — `auth/service.py` builds the emailed link from it.

**The magic-link route is single-use and effects mount twice in dev.**
`MagicLinkVerifier` guards with a ref; without it strict mode burns the token
on the first run and reports "already used" on the second.

---

## Test harness notes

- Integration tests need real Postgres, Redis, and MinIO. `pnpm services:up`.
- `fresh_db` fixture: asyncpg connections are bound to the event loop that
  opened them, and pytest-asyncio gives each test its own loop. Tests that
  touch the database *directly* must request `fresh_db`, or the second one in
  a module dies with "Event loop is closed". Tests going through the `client`
  fixture get this free via the app lifespan.
- `_reset_rate_limits` is pulled in by `client`, not autouse — an autouse async
  fixture breaks the synchronous metric unit tests.
- `fresh_redis` is the Redis counterpart to `fresh_db`, and the same rule
  applies: a test that touches Redis *directly* (OAuth state, rate limits)
  must request it. Otherwise the next Redis-touching test dies inside
  `_reset_rate_limits`, which makes it look like a rate-limit bug rather than
  a leaked connection.
- Web tests mock `fetch`; there is no test server.

---

## Where the important logic lives

```
apps/api/app/core/methodology.py            every threshold, versioned
apps/api/app/modules/metrics/qualification.py   what counts as an observation
apps/api/app/modules/metrics/calculator.py      aggregation + suppression
apps/api/app/modules/verification/service.py    moderation, one transaction
apps/api/app/modules/disputes/service.py        corrections
apps/api/app/modules/companies/normalize.py     Korean name dedupe
apps/web/lib/format/metrics.ts                  suppression, UI side
apps/web/components/brand/svg/paths.ts          mascot geometry, authored once
```

Moderation is one transaction: review row, status change, audit entry,
reputation ledger, and metric recompute all commit together or none do.

---

## Current state

**Deployment is the next session's work, and none of it exists yet** — no
Dockerfile, no hosting config, no deploy job, no production data stores. See
`docs/NEXT_SESSION.md`, which starts from the one decision the rest depends
on: the production hostname layout, because the session cookie is host-only
and `SameSite=Lax`.



The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
closed except for **Korean legal review of the privacy policy and terms**. That
is the remaining blocker before real-company metrics can go public, and it is
not an engineering task.

Real company data has **not** been imported yet — this is deliberate, pending
that review. Development runs on fictional fixtures (`pnpm api:seed`), all
flagged `is_demo` and labelled `샘플 데이터` in the UI.

Phase 4 is now visible: `/me` renders rank, both ledgers, and badges from
the engine that was already running. `pnpm api:seed` awards standing through
the real `reputation_service.award` path rather than inserting ledger rows,
so ranks and badges are exercised in development.

Sign-in works end to end on the web: `/sign-in` (Google + magic link),
`/auth/verify`, `/me/reports`, and session state in the header. Google is
dark until `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set — the sign-in
page asks `/auth/providers` and hides the button rather than offering one
that fails.

Jobs shipped with `ENABLE_JOBS=true`: `/jobs`, `/jobs/[jobId]`, and
`/companies/[slug]/jobs`, plus the outbound apply deep link. Demo postings
are seeded onto the fictional companies with `example.com` URLs, one of them
already expired so the closed-posting path stays visible.

Not built yet: saved jobs (the remaining half of docs/09 Phase 6 — it needs a
`saved_jobs` table and a migration), community, the application tracker,
company claim verification, `/dex` leaderboards (intentionally closed until
enough companies clear the sample bar), and share cards.

---

## Conventions

- Korean copy: short, factual, dry. Never `쓰레기 회사`, `악덕 기업`, `박제`.
  Approved vocabulary is in `docs/handoff/docs/02_BRAND_AND_VISUAL_SYSTEM.md`.
- **No emoji as illustration, anywhere.** The SVG family in
  `components/brand/svg/` is original and covers the cases. Adding a new mark
  means drawing one.
- Positive and negative states get equal visual weight. `답장 생존` is as
  saturated as `멸종위기` by design.
- Every metric shown must carry its sample size and window.
- Never invent negative records about a real company, in fixtures or anywhere.
