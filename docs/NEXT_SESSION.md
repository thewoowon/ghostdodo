# Next session

Written 2026-09-01, replacing the deployment plan that this session carried
out. Read `CLAUDE.md` first, then this.

---

## What just changed

Deployment exists in the repository. The hostname question that the previous
note called "the one decision that unblocks the rest" is answered: **one
public origin**, ghostdodo.com on Vercel, with `/api/v1/*` rewritten to the
API on Railway. The session cookie therefore needed no change at all, and
CORS stopped mattering.

Shipped with it:

- `apps/api/Dockerfile` — uv, Python 3.12, two stages, non-root.
- `apps/api/railway.json` — Dockerfile build, `/health/ready` check, and
  `alembic upgrade head` as the pre-deploy command, so the schema is in
  place before the container takes traffic.
- `apps/web/vercel.json` and the `/api/v1` rewrite in `next.config.ts`.
- Deploy jobs in `.github/workflows/ci.yml`, gated on the test jobs, API
  first.
- A real mail provider (`app/core/email.py`, Resend), because
  `EMAIL_PROVIDER=console` is now refused at boot in production — a logged
  magic link is a working sign-in.
- Three production-only correctness fixes found on the way: `client_ip`
  counts `X-Forwarded-For` from the right, `DATABASE_URL` gets the asyncpg
  driver it needs, and `check_production_hardening` covers the new ground.
  All covered by `apps/api/tests/test_deployment.py`.

Verified: `pnpm api:test` (157), `pnpm test` (70), `pnpm api:lint`,
`pnpm typecheck`, `pnpm lint`, `pnpm build`, plus `docker build` and a
container smoke test against local Postgres and Redis.

## What is left of it

Account work only, and it is a step-by-step runbook in
`docs/DEPLOYMENT.md`: the private S3 bucket, the Resend domain, the two
projects, the DNS records, the Google OAuth redirect URI, and the CI
secrets. Nothing in it needs a code change.

Two things worth doing deliberately once it is up, because they fail
silently rather than loudly:

1. The **rate-limit smoke test** — if `TRUSTED_PROXY_HOPS` is wrong, every
   page still works and the whole site shares one bucket.
2. **Postgres backups** on Railway. The append-only ledgers make
   point-in-time recovery meaningful.

---

## Then, in order

1. **Saved jobs** — the remaining half of docs/09 Phase 6. Needs a
   `saved_jobs` table and a migration, mirroring `SavedCompany`.
2. **Share cards.**
3. **Community** (Phase 5). `community/` has only `models.py`.
4. **Application tracker** (Phase 7). `applications/` is an empty directory.
5. Company claim verification, then `/dex` leaderboards — the latter stays
   closed until enough companies clear the sample bar, which is a data
   question, not an engineering one.

---

## Still not an engineering task

The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
closed except for **Korean legal review of the privacy policy and terms**.
Deploying did not change that. Until it closes, only the five fictional demo
companies may exist in production.

Both documents were brought up to the statutory checklist on 2026-09-02 and
`docs/legal/REVIEW_REQUEST.md` is the package to hand counsel. What comes
back may create engineering work, and two answers in particular:

- **국외 이전** — if the answer is that account data cannot sit on Railway in
  the US, hosting changes. Ask this before provisioning anything.
- **임시조치** — a takedown obligation that pulls against "a company cannot
  delete a record". Whatever counsel says, do not resolve it by giving
  companies a delete path.

Also outstanding, and now written into the privacy policy as a manual
process: **there is no account deletion endpoint.** `deactivated_at` exists
on the model and nothing sets it. Building `DELETE /me` is a small piece of
work, and it would let the policy promise a button instead of a mailbox.
