# 09. Roadmap & Acceptance Criteria

## Phase 0 — Foundation

Deliver:
- monorepo
- Next.js/FastAPI boot
- PostgreSQL/Redis local compose
- auth skeleton
- lint/format/test
- CI

Acceptance:
- one command boots local stack
- migrations run cleanly
- web/API health checks pass

## Phase 1 — Brand shell

Deliver:
- landing
- custom SVG GhostDodo mascot family
- responsive nav/footer
- company search UI
- no fake data

Acceptance:
- zero emoji-dependent primary illustrations
- Lighthouse/accessibility baseline acceptable
- hero exactly communicates product in 5 seconds

## Phase 2 — Company database

Deliver:
- company search
- company detail
- metrics API
- insufficient-data states
- Ghostory skeleton

Acceptance:
- search handles Korean aliases
- all metrics show n/window
- zero invented public metrics

## Phase 3 — Reporting + verification

Deliver:
- report wizard
- evidence upload
- moderation queue
- verification states
- audit log

Acceptance:
- evidence is never publicly fetchable
- duplicate submission protection
- moderator can verify/reject/redact/dispute
- metric recompute occurs after status change

## Phase 4 — Reputation

Deliver:
- reputation ledger
- Dodo Credit ledger
- badges/ranks
- profile

Acceptance:
- negative reports do not intrinsically award more
- reversal removes/rebalances earned trust if appropriate
- ledger is auditable

## Phase 5 — Community

Deliver:
- posts/comments
- company tags
- helpful voting
- moderation/reporting

Acceptance:
- personal recruiter names blocked/moderatable
- rate limits in place
- data-linked posts preferred in UX

## Phase 6 — Jobs

Deliver:
- job posting model
- company jobs tab
- outbound application deep-link
- saved jobs

Acceptance:
- source attribution visible
- expired links manageable
- outbound click analytics

## Phase 7 — Application tracker

Deliver:
- saved application
- stage timeline
- expected-result date
- manual result update
- opt-in “convert to GhostDodo observation”

Acceptance:
- no tracked application becomes public without explicit user action/consent

## Launch metrics

Product:
- search → company page CTR
- company page → report start
- report completion
- evidence attach rate
- verification yield
- repeat contributor rate
- outbound job apply CTR

Trust:
- report reversal rate
- dispute rate
- PII moderation rate
- suspicious cluster rate
- verified data share

Do not use raw outrage engagement as a north-star metric.
