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

The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
closed except for **Korean legal review of the privacy policy and terms**. That
is the remaining blocker before real-company metrics can go public, and it is
not an engineering task.

Real company data has **not** been imported yet — this is deliberate, pending
that review. Development runs on fictional fixtures (`pnpm api:seed`), all
flagged `is_demo` and labelled `샘플 데이터` in the UI.

Not built yet: community, jobs and outbound tracking, the application tracker,
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
