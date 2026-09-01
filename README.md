# GhostDodo

> **지원하기 전에, 답은 해주는 회사인지 확인하세요.**
> 답장이 멸종된 회사들을 기록합니다.

GhostDodo is a Korean recruitment **communication transparency** database. It
records how companies communicate with applicants — whether a result was
delivered, how long it took, at which stage communication stopped, and how
reliably those reports were verified.

It is not a blacklist and not a rage board. It publishes **structured events
and aggregates**, with sample size and time window attached to every number.

---

## The three rules that shape the codebase

If you change one thing here, understand these first. They are enforced in
code and covered by tests, not just documented.

1. **A rate the sample cannot support is not published.** Below the
   methodology's bar the API returns `null` for every rate — never a small
   number — and the UI renders `표본 부족`. See
   [`calculator.py`](apps/api/app/modules/metrics/calculator.py) and
   [`metrics.ts`](apps/web/lib/format/metrics.ts).
2. **A rejection email is a successful response.** Response Rate measures
   explicit disposition, not good news. See
   [`qualification.py`](apps/api/app/modules/metrics/qualification.py).
3. **Thresholds are configuration, never literals.** Every observation window,
   grace period, and sample bar lives in
   [`methodology.py`](apps/api/app/core/methodology.py) under a version id.
   The public `/methodology` page renders from that same source, so the page
   and the numbers cannot disagree.

Two more that matter just as much: **evidence is private** (signed URLs only,
every moderator view audit-logged), and **reporter identity is never exposed**
— not publicly, and not to a company during a dispute.

---

## Stack

| | |
|---|---|
| Web | Next.js 16.3.3 (App Router), React 19, TypeScript strict, pnpm |
| API | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2 async, Alembic, uv |
| Data | PostgreSQL 16 (`pg_trgm` for Korean fuzzy search), Redis |
| Storage | S3-compatible, private bucket (MinIO locally) |

```text
apps/web     Next.js app — brand system, company pages, report wizard
apps/api     FastAPI modular monolith
infra        docker compose for Postgres / Redis / MinIO
docs/handoff original product & engineering handoff
```

---

## Getting started

Requires Node 22+, pnpm 11+, uv, and Docker.

```bash
cp .env.example .env
pnpm install

pnpm services:up      # Postgres, Redis, MinIO (creates the private bucket)
pnpm api:migrate      # apply migrations
pnpm api:seed         # fictional demo companies, all flagged is_demo

pnpm api:dev          # API  → http://localhost:8000  (docs at /docs)
pnpm dev              # web  → http://localhost:3000
```

### Everyday commands

```bash
pnpm typecheck / lint / test / build   # web
pnpm api:test                          # pytest
pnpm api:lint                          # ruff + mypy
pnpm services:reset                    # wipe local data volumes
```

---

## Seed data

Demo companies are **fictional** — 도도랩, 철새테크, 화석소프트, 날개코퍼레이션,
알깍스튜디오 — and every row is flagged `is_demo`, which the UI surfaces as a
`샘플 데이터` label. Each one is shaped to exercise a different metric state,
including one deliberately under the publishable bar so the suppression path
stays visible in development.

**Never invent negative records about a real company.** Real company metadata
may be added from lawful sources later, but public response metrics require
actual qualified user data.

---

## The vertical slice

The loop the product exists to support is asserted end-to-end in
[`test_vertical_slice.py`](apps/api/tests/test_vertical_slice.py):

open the site → find a company with no data → sign in → submit a structured
experience → attach private evidence → moderator verifies → aggregates
recompute → the company page reflects it → the contribution lands in the
reputation ledger.

Moderation is one transaction: the review row, status change, audit entry,
reputation ledger, and metric recompute all commit together or none do.

---

## Company directory

Search is only useful if the companies are in it. Names come from lawful
public registries:

```bash
# 금융감독원 DART — official names for listed and reporting companies
export DART_API_KEY=...          # free key: https://opendart.fss.or.kr
uv run python -m app.scripts.import_companies dart --listed-only

# 국민연금 가입 사업장 — broad coverage including private employers
# bulk CSV from https://www.data.go.kr/data/3046071/openapi.do
uv run python -m app.scripts.import_companies nps nps.csv --min-headcount 20
```

**Importing a name does not create a metric.** An imported company starts at
zero observations and reads `표본 부족` until real applicants file qualified
reports. `TestImportCreatesNoMetrics` asserts it.

Name normalization is load-bearing: `주식회사 카카오`, `(주)카카오`,
`카카오(주)`, and `카카오` must resolve to one company, or the observations
split and every fragment stays under the publishable bar forever.

---

## Reputation

Standing is earned by complete, verifiable contribution — never by what a
report said about a company. The award amounts are identical whether a
company answered in three days or never; `badges.py` follows the same rule,
and higher ranks additionally require demonstrated accuracy rather than raw
points. `/me` shows the rank, both append-only ledgers, and badges, with
every line carrying its own delta and resulting balance.

Dodo Credit is product utility, never currency. Nothing in the UI describes
it in monetary terms, and a test asserts the copy stays that way.

## Sign-in

Two providers, one account. **Google** (server-side authorization code flow)
and the original **email magic link** both resolve to the same `users` row on
a verified address, so a contributor who switches keeps their reports,
reputation, and handle. There is no separate signup step — the first sign-in
creates the account and assigns a pseudonymous handle.

Google is matched on the stable `sub` first and the verified email second.
Matching on email alone would hand an account to whoever inherits an old
address; `email_verified` is required, or one account could assert another's
address.

Google stays off until credentials exist. `GET /auth/providers` reports what
the API can actually complete, and the sign-in page renders its button from
that answer rather than from its own env — so the page can never offer a
button that leads nowhere. Without credentials the magic link still works.

```bash
# https://console.cloud.google.com/apis/credentials → OAuth client (Web)
# Authorized redirect URI: http://localhost:8000/api/v1/auth/google/callback
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Locally, `EMAIL_PROVIDER=console` prints the magic link to the API log, and
the sign-in page offers a direct link from the `dev_token` the API returns
outside production. Neither survives a deployment: `console` writes a working
sign-in to the log, so production refuses to boot with it, and `dev_token` is
gated on `expose_dev_tokens` — development and test only, staging included in
the refusal.

## Jobs

`/jobs` lists linked postings; `/companies/[slug]/jobs` is one company's tab.
GhostDodo never hosts an application — `지원하러 가기` is a real anchor to the
employer or job board, and the click is counted alongside the navigation
rather than in front of it, so accounting can never be what stops someone
from applying.

A posting establishes that a company is hiring. It says nothing about how
that company answers, so **no posting feeds a metric** — the same rule the
directory importer lives under, asserted by `TestPostingsCreateNoMetrics`.
The job page puts the company's response record above the apply button,
suppression and sample size included.

Postings sit behind `ENABLE_JOBS`. Expiry is derived from `is_active` and
`closes_on` rather than swept: a closed posting drops out of listings but
still resolves by id, so a shared link explains itself instead of 404ing.

## Deployment

One public origin. `ghostdodo.com` is served by Vercel, and `/api/v1/*` is
rewritten to the API on Railway — so the session cookie stays host-only and
same-site, and there is no CORS or CSRF story to maintain. Evidence lives in
a private S3 bucket, reachable only through signed URLs.

The API ships as a container (`apps/api/Dockerfile`); `railway.json` runs
`alembic upgrade head` before the new one takes traffic. Both deploys are
driven from CI so nothing ships that the test jobs have not gone green on.

Everything above is in the repository. The account work — bucket, mail
domain, projects, DNS, OAuth redirect URI — is a step-by-step runbook in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

```bash
docker build -t ghostdodo-api apps/api    # what Railway builds
```

---

## Public launch gate

docs/08 §11 lists what must work before real-company metrics go public:

| | |
|---|---|
| Methodology page | ✅ rendered from the API's own config |
| Report qualification thresholds | ✅ versioned in `methodology.py` |
| Sample-size suppression | ✅ enforced in API and UI, tested both sides |
| Evidence is private | ✅ signed URLs only, every view audit-logged |
| Correction / dispute flow works | ✅ open route → moderation → recompute |
| Moderation console works | ✅ `/admin/reports`, `/admin/disputes` |
| Privacy policy & terms | ⚠️ review-ready, **pending Korean legal review** |

The last row is the remaining blocker, and it is not an engineering task.
Both documents now carry the mandatory sections of 개인정보 보호법 제30조 —
processing consignment and cross-border transfer, destruction procedure, the
CPO contact, cookies, security measures, and remedies — and the terms cover
contract formation, termination, governing law, and the change-notice
periods. `docs/legal/REVIEW_REQUEST.md` is the package for counsel: the data
inventory, and the seven questions only a lawyer can answer. The sharpest of
them is the tension between 정보통신망법 제44조의2 (임시조치) and the product
rule that a company cannot delete a record.

---

## Status

Built and verified: monorepo, infra, the schema with migrations, the metric
engine, Google and magic-link sign-in with the web surface for both, reports, private evidence, moderation console, correction and
dispute resolution, reputation ledgers, the company directory importers,
linked job postings with the outbound apply deep link, the brand SVG system,
and the public pages including the report wizard.

Not yet built: saved jobs, community, the application tracker, company claim
verification, `/dex` leaderboards (intentionally closed until enough
companies clear the sample bar), and share card generation.

See [`docs/handoff/docs/09_ROADMAP_ACCEPTANCE.md`](docs/handoff/docs/09_ROADMAP_ACCEPTANCE.md).
