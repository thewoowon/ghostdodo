# Next session

Written 2026-10-23, after a seven-week gap; production section updated
2026-11-13. Read `CLAUDE.md` first, then this.

---

## What is actually live (checked 2026-11-13)

- **ghostdodo.com** is on Vercel DNS. The apex is canonical and www 308s
  to it.
- **Vercel** project `lovekong/ghostdodo-web`.
- **Railway** project `ghostdodo`: the services are `ghostdodo` (API),
  Postgres, and Redis. The API runs with `APP_ENV=production` and the
  runbook's variables. DB and Redis are wired by reference
  (`${{Postgres.DATABASE_URL}}`), mail goes through Resend, and evidence
  goes to AWS S3 `ghostdodo-evidence` in ap-northeast-2.
  `/health/ready` reports both checks `ok`, and `/docs` is closed.

How it got here, because each step is easy to repeat:

- Until 2026-11-13 the API service had **no variables**. It booted in
  development mode against `localhost`. Later the local `.env` was pasted
  in, with `APP_ENV=development`, `EMAIL_PROVIDER=console`, and the
  placeholder `AUTH_SECRET`. The DB was unreachable throughout, so the
  `dev_token` sign-in bypass was never live. Never wire `DATABASE_URL`
  without `APP_ENV=production` in the same change.
- **Migrations never ran.** `apps/api/railway.json` was not being read. The
  likely cause is that Railway resolves the config file from the repo root,
  not from the service's Root Directory. With the file ignored, the
  pre-deploy `alembic upgrade head` and the health check were both inert.
  Setting the config path in the dashboard did not change that.
  Fixed in `719d21b`: the container command now runs `alembic upgrade
  head` before uvicorn. That works whatever Railway reads, and it assumes
  one replica. The first production migration ran 2026-11-13 17:55 KST.
  Why the config file is ignored is still unexplained.
- **Demo data:** run `python -m app.scripts.seed` once inside the
  container (`railway ssh`) after the first successful migration.

Still open: `privacy@ghostdodo.com` has no MX, Google sign-in is off, and
the S3 CORS rule needs `https://ghostdodo.com`. The API service also
carries leftover web-only variables (`API_ORIGIN`, `NEXT_PUBLIC_*`). The API
ignores them, but they are misleading.

## Local state

- All checks green: API 158 tests, web 70, ruff/mypy, typecheck, lint, build.
- Fixed today: stage breakdown came back in JSONB key order (코딩/필기
  before 지원). `CompanyMetricsOut.from_snapshot` now restores hiring order,
  with a regression test.

## Operating constraint worth knowing

Only `VERIFIED` and `PARTIALLY_VERIFIED` reports enter aggregates, so every
report needs a moderator decision before it counts. With one operator,
moderation throughput *is* data throughput. Any growth push has to plan
for review time.

## Next session starts here

1. **Mobile.** The site is not optimised for phones, and the header (GNB)
   is the worst of it. The user asked for this first.
2. The sign-in page shows the Google button on first paint and hides it
   once `/auth/providers` answers. It should render nothing until it knows.
3. Smoke tests not yet run in production: evidence upload (S3 CORS), and
   the rate-limit check that proves `TRUSTED_PROXY_HOPS` is right.

Production access from this machine: the SSH key `aepeul-mac` is
registered with Railway. `railway ssh` needs a known-hosts entry first.
To run a one-off command, write a config with `railway ssh config --path
<file> --alias gd-prod` and use `ssh -F <file> gd-prod '<cmd>'`.

## Plan agreed in direction (not yet started)

The risk is cold start, not code. A company publishes rates only at n≥15
with ≥30% verified. Engineering that helps, in order:

1. Fix production (above), then run the smoke test in `docs/DEPLOYMENT.md`.
2. **Quick log.** One applicant has typically applied to dozens of
   companies. Today that means one 8-step wizard per company. A fast
   multi-company entry is the biggest lever on volume.
3. **Personal share card.** Shows the applicant's own record: applied N,
   answered M, silent K. It names no company, so it can be shared before any
   company crosses the bar, and it carries less legal risk.
4. **Company share cards** (OG images). Today the company pages carry text
   OpenGraph only.
5. **Archive-wide aggregates.** Numbers across the whole archive, with no
   company named. These are publishable long before any single company is,
   and they are what press will quote.
6. `DELETE /me`. Counsel will likely ask for it, and the privacy policy
   wording changes with it.

Deferred until there is traction: saved jobs, community, tracker, claims,
`/dex` lists.

## Still not an engineering task

Korean legal review is still the public launch gate. Two related decisions
are open: who the operator is (individual or registered business), and
who is named as 개인정보 보호책임자. The policy currently says only
"고스트도도 운영자".
