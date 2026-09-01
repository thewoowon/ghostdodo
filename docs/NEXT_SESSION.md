# Next session — deployment

Written 2026-09-01. Everything below is unstarted; the app itself runs.

Read `CLAUDE.md` first for the rules that must not break, then this.

---

## Where things stand

Roadmap (`docs/handoff/docs/09_ROADMAP_ACCEPTANCE.md`): **Phase 0–4 and 6 are
done**, including the web surfaces for sign-in and reputation. Phase 5
(community) and Phase 7 (application tracker) are not started — `community/`
has only `models.py`, `applications/` is an empty directory.

Everything is verified locally: `pnpm api:test` (136), `pnpm test` (67),
`pnpm api:lint`, `pnpm typecheck`, `pnpm lint`, `pnpm build`.

**There is no deployment anything.** No Dockerfile, no hosting config, no
deploy job in CI, no production Postgres/Redis/S3. `infra/docker-compose.yml`
is local services only. That is the whole of the next session's work.

---

## The one decision that unblocks the rest

**Where does this run, and on what hostnames?** Everything below depends on
it, so decide it first rather than building around both options.

The session cookie is the reason it matters. `_set_session_cookie` in
`apps/api/app/modules/auth/router.py` sets a host-only cookie with
`SameSite=Lax`. Locally that works because cookies ignore ports, so a cookie
set by `localhost:8000` is sent to `localhost:3000`. In production it depends
entirely on the hostnames:

| Layout | Cookie change needed |
|---|---|
| One host, API reverse-proxied under `/api` | **None.** Same origin, `Lax` is correct, and CORS stops mattering. |
| `ghostdodo.com` + `api.ghostdodo.com` | `Domain=.ghostdodo.com` on the cookie. Stays `Lax` — a subdomain is same-site. |
| Different registrable domains | `SameSite=None; Secure`, and the CSRF story has to be rebuilt. Avoid. |

Recommendation: **one host with the API proxied under a path.** It deletes the
cookie problem, the CORS problem, and the `NEXT_PUBLIC_API_BASE_URL` problem
in one move, and nothing in the codebase assumes separate origins.

---

## Work, in order

1. **Pick the hosting target and hostname layout** (above).

2. **Cookie/CORS for that layout.** Touches `_set_session_cookie` and
   `Settings.cors_origins`. If the layout is single-host, the change is
   mostly deleting CORS special-casing.

3. **Dockerfiles.** Two: `apps/api` (uv, Python 3.12) and `apps/web`
   (Next standalone output — `output: "standalone"` is not set in
   `next.config.ts` yet and will be needed).

4. **Provision.** Postgres 16 with `pg_trgm`, Redis, and a **private**
   S3 bucket. Evidence privacy is a launch-gate item: the bucket must have
   no public read path, signed URLs only.

5. **Secrets.** `AUTH_SECRET` ≥32 random chars, real `S3_SECRET_KEY`,
   `WEB_BASE_URL` on https. `check_production_hardening()` refuses to boot
   if any placeholder survives — trust it, don't work around it.

6. **CI deploy job.** `.github/workflows/ci.yml` currently only tests. Add a
   deploy that runs `alembic upgrade head` before the app rolls.

7. **Google OAuth credentials.** Only possible once the domain exists.
   Register `https://<host>/api/v1/auth/google/callback` as an Authorized
   redirect URI and set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`. Until
   then `/auth/providers` reports `google: false` and the sign-in page hides
   the button — the magic link keeps working, so this does not block a
   deploy.

---

## Still not an engineering task

The public launch gate (`docs/handoff/docs/08_TRUST_SAFETY_LEGAL.md` §11) is
closed except for **Korean legal review of the privacy policy and terms**.
Deploying does not change that: until it closes, only the five fictional demo
companies may be present. Run the review in parallel.

---

## After deployment

In the agreed order: saved jobs (last piece of Phase 6 — needs a `saved_jobs`
table and migration, mirroring `SavedCompany`), share cards, community
(Phase 5), application tracker (Phase 7), then company claim verification and
`/dex` leaderboards.
