# Deployment

Web on **Vercel**, API on **Railway**, one public origin: **ghostdodo.com**.

Everything in this file that is *code* is done and verified. What remains is
account work — creating the services, pasting the environment variables, and
pointing DNS. Do it in the order below; each step depends on the one before.

> The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
> still closed on Korean legal review of the privacy policy and terms.
> Deploying does not open it. Until it closes, only the five fictional demo
> companies may exist in the production database.

---

## The layout, and why

```
                    ┌──────────────────────────────────────────┐
  browser  ────────▶│  ghostdodo.com            (Vercel)       │
                    │                                          │
                    │   /*         → Next.js                   │
                    │   /api/v1/*  → rewrite ──────────┐       │
                    └──────────────────────────────────┼───────┘
                                                       │
                                                       ▼
                                       ┌───────────────────────────────┐
   Server Components ─────────────────▶│  Railway (FastAPI, Docker)    │
   (skip the proxy, API_ORIGIN)        │   Postgres 16 · Redis         │
                                       └───────────────────────────────┘
                                                       │
                                                       ▼
                                             AWS S3 (private bucket)
```

**One origin is the whole point.** The session cookie is host-only and
`SameSite=Lax`; locally that works only because cookies ignore ports. Serving
the API as a path on the web origin means the cookie the API sets is a cookie
for `ghostdodo.com`, CORS never enters the picture, and there is no CSRF story
to rebuild. Nothing in the codebase assumes separate origins, and after this
change nothing does in production either.

The browser therefore never learns the API's real address. Two consequences
worth knowing:

- `NEXT_PUBLIC_API_BASE_URL` is the **relative** path `/api/v1`.
- Server Components would have to resolve that against nothing, so they use
  `API_ORIGIN` and address Railway directly — one less hop, and the Vercel
  proxy is not in the path of server-side rendering.

Railway's own `*.up.railway.app` hostname stays reachable; Vercel needs a
public address to proxy to. Reaching it directly gets you the same API with
CORS refusing the origin and a cookie scoped to a hostname nobody visits. The
one thing it does allow is forging `X-Forwarded-For`, which is why
`client_ip` counts hops from the right — see **TRUSTED_PROXY_HOPS** below.

---

## 1. AWS S3 — the evidence bucket

Evidence privacy is a launch-gate item. The bucket is private, always; the
only ways bytes move are a presigned POST for the uploader and a presigned
GET for a moderator, and every moderator view is audit-logged before the URL
is minted.

1. Create a bucket in **ap-northeast-2** (Seoul). Name it
   `ghostdodo-evidence`.
2. Leave **Block all public access** ON. Do not add a bucket policy. Do not
   enable static website hosting.
3. Add a CORS rule — the browser uploads to S3 directly, so the bucket must
   accept a cross-origin POST from the site:

   ```json
   [
     {
       "AllowedOrigins": ["https://ghostdodo.com"],
       "AllowedMethods": ["POST"],
       "AllowedHeaders": ["*"],
       "ExposeHeaders": ["ETag"],
       "MaxAgeSeconds": 3000
     }
   ]
   ```

4. Create an IAM user with programmatic access and *only* these actions, on
   `arn:aws:s3:::ghostdodo-evidence/*`: `s3:PutObject`, `s3:GetObject`,
   `s3:DeleteObject`, `s3:HeadObject` (`HeadObject` is covered by
   `GetObject`). Nothing bucket-level, no `s3:ListBucket`.
5. Turn on a lifecycle rule only if you have decided a retention period —
   `docs/handoff` sets evidence retention, not this file.

**Not Cloudflare R2.** R2's S3 API does not implement `POST Object`, and
`create_upload_url` uses a presigned POST specifically so the *bucket*
rejects an oversize upload before the bytes land. On R2 that first line of
defence disappears and the upload path has to be rewritten around a signed
PUT. Other S3-compatible providers need the same check before being chosen.

## 2. Resend — magic-link delivery

Without this, sign-in has no working provider: Google is dark until its
credentials exist, and `EMAIL_PROVIDER=console` is refused at boot in
production because a logged magic link is a working sign-in for anyone who
can read the log.

1. Add and verify the domain `ghostdodo.com` (Resend prints the DKIM/SPF
   records to add at your DNS host).
2. Create an API key → `RESEND_API_KEY`.
3. `EMAIL_FROM` must be on the verified domain:
   `GhostDodo <no-reply@ghostdodo.com>`.

The free tier is 100 mails/day, 3,000/month, one domain. Switching providers
later is one setting plus one function in `app/core/email.py`.

## 3. Railway — the API

1. New project → **Deploy from GitHub repo** → this repository.
2. Service settings → **Root Directory: `apps/api`**. `railway.json` there
   selects the Dockerfile, sets the health check, and runs
   `alembic upgrade head` as the pre-deploy command, so the schema is
   migrated before the new container takes traffic.
3. Add **Postgres** and **Redis** from the project's Add Service menu.
   Postgres must be 16 — `0001_bootstrap` creates `pg_trgm` and `unaccent`,
   which Korean company search depends on.
4. **Turn off automatic deploys on push.** CI deploys this service after its
   tests pass (`.github/workflows/ci.yml`); leaving Railway's own trigger on
   means every push deploys twice, once ungated.
5. Settings → Networking → **Generate Domain**. Note the
   `*.up.railway.app` hostname; Vercel needs it.

### Railway environment variables

Use Railway's reference syntax for the data stores so they follow the
services rather than being pasted copies.

| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `APP_BASE_URL` | `https://ghostdodo.com` |
| `WEB_BASE_URL` | `https://ghostdodo.com` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `AUTH_SECRET` | `openssl rand -hex 32` |
| `TRUSTED_PROXY_HOPS` | `2` |
| `EMAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | from step 2 |
| `EMAIL_FROM` | `GhostDodo <no-reply@ghostdodo.com>` |
| `S3_ENDPOINT` | `https://s3.ap-northeast-2.amazonaws.com` |
| `S3_REGION` | `ap-northeast-2` |
| `S3_BUCKET` | `ghostdodo-evidence` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | from step 1 |
| `S3_FORCE_PATH_STYLE` | `false` |
| `ENABLE_JOBS` | `true` |
| `RATE_LIMIT_ENABLED` | `true` |
| `LOG_LEVEL` | `INFO` |

Both URL variables are `https://ghostdodo.com` and neither is the Railway
hostname. `APP_BASE_URL` is what the Google callback URL is built from, and
that callback has to be an address the *browser* can reach.

`S3_REGION` must be the real region: the default `auto` is an R2-ism and AWS
SigV4 will reject it.

`DATABASE_URL` arrives as `postgresql://…`; the settings layer rewrites the
scheme to `postgresql+asyncpg://`, because SQLAlchemy would otherwise reach
for a sync driver that is not installed.

**`TRUSTED_PROXY_HOPS=2`** is Vercel's hop plus Railway's edge. It is how
`client_ip` finds the caller: it counts that many entries back from the *end*
of `X-Forwarded-For`, because everything to the left of them is whatever the
caller chose to send. Too high and a caller picks their own rate-limit
bucket; too low and every visitor shares one.

The API refuses to boot if `AUTH_SECRET` is short or a placeholder, if either
base URL is plaintext, if `EMAIL_PROVIDER` is `console`, or if the configured
mail provider has no key. Trust it — a failed boot here is the check working.

## 4. Vercel — the web app

1. New project → this repository → **Root Directory: `apps/web`**.
   `apps/web/vercel.json` sets the pnpm workspace install and the Seoul
   region.
2. **Turn off automatic deploys** (Settings → Git), for the same reason as
   Railway.
3. Environment variables (Production):

   | Variable | Value |
   |---|---|
   | `API_ORIGIN` | `https://<service>.up.railway.app` |
   | `NEXT_PUBLIC_API_BASE_URL` | `/api/v1` |
   | `NEXT_PUBLIC_APP_URL` | `https://ghostdodo.com` |

   `API_ORIGIN` does two jobs: it is where `/api/v1/*` is rewritten, and it
   is what Server Components fetch directly. The build fails on Vercel if it
   is missing, rather than silently proxying production traffic to a
   localhost that isn't there.

4. Domains → add `ghostdodo.com`, and set `www.ghostdodo.com` to redirect to
   it. Add the records Vercel shows at your DNS host.

## 5. Google sign-in

Only possible once the domain resolves. In the Google Cloud console →
Credentials → the OAuth 2.0 Web client, register exactly:

```
https://ghostdodo.com/api/v1/auth/google/callback
```

That is the *web* origin, because the API is reached through the rewrite.
Then set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` on Railway and
restart the service — **feature flags and credentials are read once, at
import**. Until then `/auth/providers` reports `google: false` and the
sign-in page hides the button rather than offering one that fails. The magic
link works without it, so this does not block a deploy.

## 6. CI deploy

`.github/workflows/ci.yml` deploys after `web` and `api` are green, API
first. Add these to the repository:

| Kind | Name | Value |
|---|---|---|
| Secret | `RAILWAY_TOKEN` | Railway project token |
| Variable | `RAILWAY_SERVICE` | the API service's name |
| Secret | `VERCEL_TOKEN` | Vercel account token |
| Secret | `VERCEL_ORG_ID` | from `.vercel/project.json` after `vercel link` |
| Secret | `VERCEL_PROJECT_ID` | same file |

A deploy already running is never cancelled by the next push; it finishes,
and the newer commit deploys behind it.

---

## First deploy — the order that works

1. S3 bucket, Resend domain (both are DNS-latency-bound; start them first).
2. Railway service + Postgres + Redis, environment variables, first deploy.
   Migrations run as the pre-deploy command. Check
   `https://<service>.up.railway.app/health/ready` returns
   `{"status":"ready"}` with both checks `ok`.
3. Vercel project, environment variables, first deploy, then the domain.
4. DNS. Wait for the certificate.
5. Google OAuth credentials → restart the API.
6. Seed the demo companies **only**:
   `railway run python -m app.scripts.seed`. They are flagged `is_demo` and
   render as `샘플 데이터`.

## Smoke test, in order

Each of these fails differently, so run them in sequence rather than
declaring victory on the home page rendering.

| Check | Confirms |
|---|---|
| `GET /` renders a company page with `표본 부족` on the under-bar company | The rewrite works and suppression survives to production |
| `GET /api/v1/methodology` | The proxy path reaches the API |
| Sign in by magic link, end to end | Resend, `WEB_BASE_URL`, and the single-use token |
| The header shows the handle after verifying | **The cookie crossed the proxy.** This is the one that fails if the layout is wrong |
| `/me` shows rank and both ledgers | Session reaches authenticated Server Components |
| Submit a report with an attachment | S3 CORS and the presigned POST |
| A second sign-in attempt from the same address within a minute is refused | Rate limiting has a real client address, not the proxy's |

That last one is worth doing deliberately. If `TRUSTED_PROXY_HOPS` is wrong,
everything above still passes and the whole site quietly shares one
rate-limit bucket.

---

## Known, and deliberate

- **`/docs` and `/openapi.json` are open on staging**, closed in production.
  The schema is not a secret; `dev_token` is, and that is gated separately
  on `expose_dev_tokens`.
- **The Railway hostname is reachable directly.** The proxy needs a public
  address. See the `TRUSTED_PROXY_HOPS` note above for the only consequence.
- **No staging environment.** When one exists it needs its own bucket,
  its own Resend domain or a sandbox address, and `APP_ENV=staging` — which
  already disables `dev_token`.
- **No backups configured.** Railway's Postgres has its own backup settings;
  the append-only ledgers (`reputation_events`, `credit_ledger`,
  `audit_logs`) make point-in-time recovery meaningful, so turn them on.
