# Next session

Written 2026-10-23; last updated at the end of the 2026-11-13/14 session.
Read `CLAUDE.md` first, then this. Start at "Next session starts here".

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

**Live and verified in production, 2026-11-13 19:12 KST.**
`PROXY_SHARED_SECRET` is set on both sides and `TRUSTED_PROXY_HOPS=1` on
Railway. One request was sent with a spoofed `X-Forwarded-For` and a forged
`X-GD-Client-IP`/`X-GD-Proxy-Secret` pair, and the stored hash matched the
real address. To recheck after any proxy or hosting change, send that same
request. The script's whole logic is "select the newest token row and
compare its hash with `hash_ip(candidate)`", run with `PYTHONPATH=/app`.

## Local state (end of 2026-11-14 session)

- All checks green: API 201 tests, ruff, mypy; web 103 tests, typecheck,
  lint, build. Everything is pushed and deployed; `git log origin/main`
  is the record.
- The local DB mirrors production's directory: about 72k real companies,
  with brand aliases. Local browser scripts must file reports against
  **demo** companies only.
- Shipped in the 2026-11-13/14 session:
  - The mobile pass: header menu, tables, sign-in.
  - The client-IP fix, which keeps rate limits per visitor.
  - The publication gate, and the real-company import behind it.
  - The company-request queue and the quick log.
  - Jobs closed.
  - Size-ranked search, and brand aliases.

## 2026-11-14

- **Jobs are closed in production.** Railway has `ENABLE_JOBS=false`, and
  the menu entry needs `NEXT_PUBLIC_ENABLE_JOBS=true`. The only postings
  were demo fixtures. A lawful source would be the 고용24 Open-API (apply
  for a key, then check the redistribution terms). Never crawl private
  boards.
- **Search lifts large employers** (2d0fcce). Exact name first, then
  similarity plus a size boost. The import keeps the largest workplace band.
  Production bands were corrected by re-running the NPS import on
  2026-11-14: 0 created, 78,614 updated, then DART `--update-only` again.
  Note that NPS overwrites DART's official names, so always run DART after
  NPS.
- **Brand aliases** (aceb780). `sources/brand_aliases.csv` has 46 reviewed
  rows, applied with `import_companies aliases` (try `--dry-run` first).
  The user reviewed the list, and all 46 were applied in production on
  2026-11-14 (dry run first, 0 unresolved). To add more, edit the CSV,
  dry-run, then apply. Re-running is safe because existing aliases count as
  `already`.
- **Data gaps seen while building aliases:**
  - 엔씨소프트 and 지에스칼텍스 are not in the directory.
  - Workplace variants still stand alone: `한화에어로스페이스 창원사업장`,
    `씨제이올리브영 -비정규`. `employer_name()` could fold `…사업장` and
    `-비정규`, but it needs a dry-run count first.

## Operating constraint worth knowing

Only `VERIFIED` and `PARTIALLY_VERIFIED` reports enter aggregates, so every
report needs a moderator decision before it counts. With one operator,
moderation throughput *is* data throughput. Any growth push has to plan
for review time.

## State of production (2026-11-14)

- **72,305 companies**: 72,300 real and 5 demo. The source was NPS 2026-09
  (법인, 20+ members, active), with site and programme workplaces folded
  into the employer. DART `--update-only` added official names and
  tickers to 2,359 companies, and 46 brand aliases are applied. The
  monthly refresh is the same commands in this order: NPS, then DART
  `--update-only`, then `aliases`. NPS overwrites DART's names.
- **Every real company is held back** (`PUBLISH_REAL_COMPANIES` off) and
  verified live: no rates, no cards, no counts, `공개 준비 중`, `noindex`.
  Turning it on is the whole launch, after legal review.
- **The operator moderates**: `dodo_01cb2592` has MODERATOR. Queues:
  `/admin/reports` (with quick-log batches), `/admin/disputes`, and
  `/admin/companies`.
- **Jobs are closed** (`ENABLE_JOBS=false`; the web flag is off).
- **Rate limits see the visitor** (`PROXY_SHARED_SECRET` on both sides,
  `TRUSTED_PROXY_HOPS=1`).

## Next session starts here

**Waiting on the user (not engineering):**
1. **Evidence upload, end to end.** File a real application through
   `/report/quick` or `/report/new` with an attachment, then review it in
   `/admin/reports`. S3 CORS is already confirmed.
2. **Missing large employers**: 엔씨소프트 and 지에스칼텍스 are not in the
   NPS data. Add them through the company-request queue.
3. **Apply for a 고용24 Open-API key** if jobs should reopen; check the
   redistribution terms before building on it.
4. **Korean legal review** (see the end of this file), now including Q8 on
   collecting before publishing.

**Engineering, in order:**
1. **Fold leftover workplace names into their employer.** Two kinds still
   stand alone: `한화에어로스페이스 창원사업장`, and `씨제이올리브영 -비정규`
   (see 2026-11-14 above). Extend `nps.employer_name()` for `…사업장` and
   `-비정규`. Dry-run the count and samples, then re-import. Duplicates
   that already exist need a merge step, because a re-import only adds
   the folded name and never deletes the old row.
2. **Personal share card** (plan item 3 below).
3. Then company OG cards, archive-wide aggregates, and `DELETE /me`.

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
2. ~~Quick log~~. **Built 2026-11-13 (5bea5b3):**
   - `/report/quick` takes shared fields once and one line per company,
     up to 30 lines counted as one submission.
   - The last contact date is required once past the application.
   - Lines share a `batch_id`. The review queue offers a batch partial
     verification, covering only lines that passed the auto-checks.
   - No reputation is awarded at submission.
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
