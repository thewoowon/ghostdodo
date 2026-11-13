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

Still open: `privacy@ghostdodo.com` has no MX, and Google sign-in is off.
The API service also carries leftover web-only variables (`API_ORIGIN`,
`NEXT_PUBLIC_*`). The API ignores them, but they are misleading.

The S3 CORS rule is in place (checked 2026-11-13): a preflight from
`https://ghostdodo.com` gets exactly the runbook's rule back, and other
origins get 403. An actual upload in production has still not been tried.

## Client IP in production (found and fixed in code 2026-11-13)

`TRUSTED_PROXY_HOPS=2` assumed the API receives
`X-Forwarded-For: <visitor>, <Vercel>`. Measured, it does not.

The check: one `POST https://ghostdodo.com/api/v1/auth/sign-in` from a
known IPv4 address, with a spoofed `X-Forwarded-For: 203.0.113.7`. In the
container, the stored `magic_link_tokens.requested_ip_hash` was compared
against `hash_ip()` of both addresses, and it matched neither. Railway staff
say the edge *overwrites* the header with whoever connected, which here is
Vercel. As a result sign-in (5 per 15 min), search, and evidence upload were
shared site-wide.

The fix, as the user chose: `proxy.ts` sends `X-GD-Client-IP` and
`X-GD-Proxy-Secret`, and the API believes the IP only with a matching
`PROXY_SHARED_SECRET`. Verified locally through `next start` in the
one-origin layout:
- Vercel-style `x-real-ip` reaches the stored hash.
- A pair forged by the browser is stripped.
- A direct hit without the secret falls back.
- The sixth sign-in is refused for one visitor while another still gets in.

**Live only once `PROXY_SHARED_SECRET` is set, identically, on Vercel and on
Railway**, with `TRUSTED_PROXY_HOPS=1` on Railway. Until then the code
behaves exactly as before. Then rerun the one-request check: the stored
hash should match the real address. The script's whole logic is "select the
newest token row and compare its hash with `hash_ip(candidate)`", run with
`PYTHONPATH=/app`.

## Local state

- All checks green: web 82 tests, typecheck, lint, build. The API was not
  touched this session (158 at last run).
- Mobile pass done 2026-11-13, checked at 360/390/768 on every public page
  plus `/me`:
  - Below 760px the header folds into a menu, with 기록하기 kept in the bar.
  - The stage table fits at phone width, so 응답 소요 was no longer hidden.
  - The sign-in email field stacks above its button.
  - `/search` stopped opening a dropdown over its own results.
- The sign-in page decides the Google button on the server, so it no
  longer flashes and vanishes.
- None of this is pushed yet, unless the git log says otherwise.

## Operating constraint worth knowing

Only `VERIFIED` and `PARTIALLY_VERIFIED` reports enter aggregates, so every
report needs a moderator decision before it counts. With one operator,
moderation throughput *is* data throughput. Any growth push has to plan
for review time.

## Next session starts here

1. **Set `PROXY_SHARED_SECRET` on Vercel and Railway, set
   `TRUSTED_PROXY_HOPS=1` on Railway, then verify** (section above).
2. Evidence upload in production, end to end. CORS is confirmed. What
   remains is a real submission with an attachment, made by the user since
   it needs their inbox. Reject the test report afterwards.
3. Smaller mobile leftover: `공고 자세히` and the inline company links on
   job cards are 21–23px tall. (`/me/reports` now names the company.)

Production access from this machine: the SSH key `aepeul-mac` is
registered with Railway, and this directory is `railway link`ed to
`ghostdodo`/production. `railway ssh` needs a known-hosts entry first, so
pass `-o StrictHostKeyChecking=accept-new`. Scripts piped into the
container need `PYTHONPATH=/app`.
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
