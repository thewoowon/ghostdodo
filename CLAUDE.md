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

**A real company publishes nothing until the launch gate opens.** While
`PUBLISH_REAL_COMPANIES` is off, a non-demo company can be found and
reported on, but no rate, no report card, and no report count about it
reaches any public response. Its page shows `공개 준비 중` and is
`noindex`. This covers more than the sample bar does: a verified card is
public the moment it is verified, with no n in between. `publishes()` in
`companies/schemas.py` is the only place that decides it, and
`tests/test_publication.py` guards it. Never turn the switch on before the
user says Korean legal review is done.

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
from `localhost:8000`. It would NOT hold across different hosts, which is why
production serves one origin: Vercel rewrites `/api/v1/*` on ghostdodo.com to
the API on Railway, so the cookie the API sets is a cookie for the site. A
change that gives the API its own public hostname reintroduces the problem
and takes CORS and CSRF with it. See `docs/DEPLOYMENT.md`.

**The visitor's IP comes from the web tier, vouched for with a secret.**
Railway's edge replaces `X-Forwarded-For` with whoever connected to it, and
for browser traffic that is Vercel. No hop count finds the visitor; this
was measured on 2026-11-13, when the whole site shared one rate-limit bucket.
`proxy.ts` sets `X-GD-Client-IP` plus `X-GD-Proxy-Secret`, and `client_ip`
believes the IP only when the secret matches, because the Railway hostname is
public. A Server Component that fetches a rate-limited endpoint directly
must pass `visitor` (see `/search`), or it is bucketed as Vercel.
`client_ip` falls back to counting `TRUSTED_PROXY_HOPS` from the *right* of
`X-Forwarded-For`; the leftmost entry is whatever the caller typed. The
container runs uvicorn *without* `--proxy-headers`, so there is exactly
one place that decides this. Get it wrong and nothing visibly breaks: the
site just shares one bucket.

**`EMAIL_PROVIDER=console` writes a working sign-in to the log.** Same class
of problem as `dev_token`, and `check_production_hardening` refuses to boot
on it. A failed magic-link send raises rather than being swallowed — a 202
means "check your mail", and it must not be the answer to a mail the
provider refused.

**Managed Postgres hands out `postgresql://`, and this engine is async.**
The settings layer rewrites the scheme to `postgresql+asyncpg://`; without
that, SQLAlchemy reaches for psycopg2, which is not installed, and the app
dies at import with an error that names nothing relevant. An explicit sync
driver is refused rather than rewritten.

**Cloudflare R2 cannot host evidence.** Its S3 API does not implement `POST
Object`, and `create_upload_url` uses a presigned POST so the *bucket*
rejects an oversize upload before the bytes land. Any S3-compatible
alternative needs that box ticked before it is chosen.

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

**Deployment is live on the runbook's layout**: Vercel
(`lovekong/ghostdodo-web`), Railway project `ghostdodo`, and AWS S3 in
Seoul. As of 2026-11-13, Railway was not reading `apps/api/railway.json`,
so migrations had never run. See `docs/NEXT_SESSION.md` before touching
deployment. The runbook is `docs/DEPLOYMENT.md`. Railway and Vercel
deploy from their own GitHub integrations; CI runs tests only.

The layout is **one origin**: ghostdodo.com on Vercel, `/api/v1/*` rewritten
to the API on Railway. That is what keeps the session cookie host-only and
same-site, and it is the reason `NEXT_PUBLIC_API_BASE_URL` is a relative
path in production while Server Components use `API_ORIGIN` directly.

The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
closed except for **Korean legal review of the privacy policy and terms**. That
is the remaining blocker before real-company metrics can go public, and it is
not an engineering task.

The two documents are now review-ready rather than drafts: the privacy policy
follows the section order of 개인정보 보호법 제30조 so a reviewer can walk it
against the statute, and both name `privacy@ghostdodo.com` as the single
intake. `docs/legal/REVIEW_REQUEST.md` carries the data inventory and the
questions for counsel. Two of the answers can change engineering:

- **Cross-border transfer.** Account data and every report live on Railway in
  the US. If counsel says that needs domestic processing, the hosting choice
  changes — cheapest to do before the first deploy.
- **임시조치 (정보통신망법 제44조의2).** A rights-infringement notice may
  oblige the operator to suspend a post, which sits directly against the
  product rule that a company cannot delete a record. Do not resolve this
  tension by quietly giving companies a delete path.

**There is no account deletion endpoint.** `deactivated_at` exists on the
model but nothing user-facing sets it, so 탈퇴 and 삭제 requests are handled
by hand through the mailbox. The privacy policy says exactly that rather than
promising a button that does not exist — if you build the endpoint, the
wording has to change with it.

On 2026-11-13 the user decided to **import real companies before review,
publish nothing about them** (see the rule above). In production only the
five demo companies could be reported on, so not one real record could be
collected. Imports are identity only: DART listed companies, and 국민연금
employers with at least 20 members. Production has held 72,300 real
companies since 2026-11-13, all `published: false`. Demo fixtures
(`pnpm api:seed`) stay
flagged `is_demo`, are labelled `샘플 데이터`, and publish either way. Counsel
has the question as Q8 in `docs/legal/REVIEW_REQUEST.md`.

Phase 4 is now visible: `/me` renders rank, both ledgers, and badges from
the engine that was already running. `pnpm api:seed` awards standing through
the real `reputation_service.award` path rather than inserting ledger rows,
so ranks and badges are exercised in development.

Sign-in works end to end on the web: `/sign-in` (Google + magic link),
`/auth/verify`, `/me/reports`, and session state in the header. Google is
dark until `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set — the sign-in
page asks `/auth/providers` and hides the button rather than offering one
that fails. The magic link now has a real sender behind it: `EMAIL_PROVIDER`
picks between `console` (dev) and `resend`, and `app/core/email.py` is the
only place that knows how a message leaves.

Jobs are built (`/jobs`, `/jobs/[jobId]`, `/companies/[slug]/jobs`, and
the outbound apply deep link) but **closed in production since
2026-11-14**. Railway has `ENABLE_JOBS=false`, and the web menu entry shows
only with `NEXT_PUBLIC_ENABLE_JOBS=true` (`lib/features.ts`). The only
postings were demo fixtures linking to `example.com`, which read as real
next to real companies. Reopen when there is a lawful source of real
postings. Never crawl private job boards: in 잡코리아 v. 사람인 (서울고법
2016나2019365), copying postings was held to infringe the board's
database right.

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
