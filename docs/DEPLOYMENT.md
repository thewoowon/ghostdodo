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
4. Deploys are triggered by Railway's own GitHub integration. Two settings
   are worth finding:
   - **Wait for CI** — holds the deploy until the checks on the commit pass,
     which is what keeps a red test suite from shipping.
   - **Watch Paths: `apps/api/**`** — otherwise a web-only commit rebuilds
     and redeploys the API for nothing.
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
| `TRUSTED_PROXY_HOPS` | `1` |
| `PROXY_SHARED_SECRET` | `openssl rand -hex 32`, the same value as on Vercel |
| `EMAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | from step 2 |
| `EMAIL_FROM` | `GhostDodo <no-reply@ghostdodo.com>` |
| `S3_ENDPOINT` | `https://s3.ap-northeast-2.amazonaws.com` |
| `S3_REGION` | `ap-northeast-2` |
| `S3_BUCKET` | `ghostdodo-evidence` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | from step 1 |
| `S3_FORCE_PATH_STYLE` | `false` |
| `ENABLE_JOBS` | `true` |
| `PUBLISH_REAL_COMPANIES` | `false` until Korean legal review closes |
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

**How the API finds the visitor.** Railway's edge *replaces*
`X-Forwarded-For` with the address that connected to it. For browser
traffic that address is Vercel's, so no hop count can find the visitor.
That was measured on 2026-11-13: the whole site was sharing one rate-limit
bucket. Instead, `proxy.ts` on Vercel names the visitor in `X-GD-Client-IP`
and vouches for it with `X-GD-Proxy-Secret`. The API believes the IP only
when the secret matches, because the Railway hostname is public. The
`/search` Server Component sends the same pair on its direct fetch.

`PROXY_SHARED_SECRET` must be identical on both sides. If either side lacks
it, nothing breaks: the API ignores the header and falls back to hop
counting, which brings back the shared bucket. So set it on both, then
verify.

**`TRUSTED_PROXY_HOPS=1`** is that fallback. It covers requests that skip
the web tier, such as a direct hit on the Railway hostname. The edge has
just overwritten the chain with the caller's own address, so one hop from
the right is the caller, not something they chose.

Verify by sending six sign-in requests through `ghostdodo.com`. The sixth
should get 429, and a request from another network should still get 202.
For a finer check, see the one-request `ip_hash` comparison in
`docs/NEXT_SESSION.md`.

The API refuses to boot if `AUTH_SECRET` is short or a placeholder, if either
base URL is plaintext, if `EMAIL_PROVIDER` is `console`, or if the configured
mail provider has no key. Trust it — a failed boot here is the check working.

## 4. Vercel — the web app

1. New project → this repository → **Root Directory: `apps/web`**.
   `apps/web/vercel.json` sets the pnpm workspace install and the Seoul
   region.
2. Vercel deploys from its own GitHub integration. Root Directory is enough
   for it to build only the web app, and it gives you a preview deploy per
   pull request for free. There is no wait-for-CI switch, but a broken build
   fails the deploy on its own.
3. Environment variables (Production):

   | Variable | Value |
   |---|---|
   | `API_ORIGIN` | `https://<service>.up.railway.app` |
   | `NEXT_PUBLIC_API_BASE_URL` | `/api/v1` |
   | `NEXT_PUBLIC_APP_URL` | `https://ghostdodo.com` |
   | `PROXY_SHARED_SECRET` | the same value as the API's |

   `API_ORIGIN` does two jobs: it is where `/api/v1/*` is rewritten (by
   `proxy.ts`, with `next.config.ts` as the fallback), and it is what Server
   Components fetch directly. `PROXY_SHARED_SECRET` is server-only. Never
   give it a `NEXT_PUBLIC_` prefix. The build fails on Vercel if it
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

## 6. CI

`.github/workflows/ci.yml` runs tests only — it does not deploy, and there
are no deployment secrets in the repository. Each provider watches GitHub
itself.

That means the two deploys are **not ordered**. Railway runs
`alembic upgrade head` before its own container rolls, so the schema is
never behind the API; but the web app can go live a few seconds before or
after. For an ordinary change that does not matter. For a change where it
would — a migration the new pages depend on — deploy the API first from the
Railway dashboard and let Vercel follow.

The API job runs Postgres and Redis as service containers and no object
storage. That is deliberate: presigning a POST or a GET is local computation
in botocore, and no test round-trips an object, so a MinIO container would
sit there testing nothing. (It used to. `bitnami/minio:latest` stopped
existing when Bitnami reorganised their Docker Hub catalogue, which is how
we found out it was never load-bearing.)

---

## First deploy — the order that works

1. S3 bucket, Resend domain (both are DNS-latency-bound; start them first),
   and the `privacy@ghostdodo.com` mailbox — the privacy policy and terms
   both name it as the only intake for 열람·정정·삭제 requests and rights
   notices, so it has to answer before launch.
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
| A sixth sign-in attempt from one network within 15 minutes is refused, and another network is not | Rate limiting sees the visitor, not the proxy (`PROXY_SHARED_SECRET` on both sides) |

That last one is worth doing deliberately. If the secret is missing or
mismatched, everything above still passes and the whole site quietly shares
one rate-limit bucket.

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
