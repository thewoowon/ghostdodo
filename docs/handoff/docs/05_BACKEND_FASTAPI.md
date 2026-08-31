# 05. Backend — FastAPI

## 1. Baseline

Use:
- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Redis
- uv

## 2. Architecture

Start as a modular monolith, not microservices.

```text
apps/api/app/
  main.py
  core/
    config.py
    security.py
    logging.py
    rate_limit.py
  db/
    session.py
    base.py
    migrations/
  modules/
    auth/
    users/
    companies/
    reports/
    evidence/
    verification/
    metrics/
    reputation/
    community/
    jobs/
    applications/
    moderation/
    disputes/
    company_claims/
  shared/
    schemas/
    enums/
    errors/
```

Each module should contain router/service/repository/schema/model as needed. Avoid ceremony where a simple module suffices.

## 3. API conventions

Base: `/api/v1`

- JSON REST API
- cursor pagination for feeds/timelines
- consistent error envelope
- idempotency key for report submission and evidence completion
- UTC in storage, Korean local dates in presentation
- UUID/ULID public identifiers; avoid sequential IDs in public URLs

## 4. Authentication

MVP options:
- email magic link OR established OAuth providers
- secure session/JWT architecture
- role claims: user, moderator, admin, company_rep

Do not expose reporter identity to companies or public users.

## 5. Evidence security

Evidence is private by default.

Architecture:
1. API creates upload intent.
2. Client uploads directly to object storage via short-lived signed URL.
3. Evidence record stores object key + mime + size + hash.
4. Moderators receive time-limited signed read URLs.
5. Public endpoints never return raw evidence location.

Add malware/type/size validation and metadata stripping strategy.

## 6. Verification pipeline

Statuses:

```text
DRAFT
SUBMITTED
AUTO_CHECKED
NEEDS_REVIEW
VERIFIED
PARTIALLY_VERIFIED
REJECTED
DISPUTED
REDACTED
REMOVED
```

MVP auto-checks:
- impossible dates
- duplicate submission hash
- same user/company/stage rapid duplication
- suspicious identical free text
- evidence file metadata
- PII warning heuristics

Human moderation remains authoritative for sensitive disputes.

## 7. Aggregation jobs

Company metrics should not be recalculated from raw rows on every request.

Use:
- materialized aggregate tables or scheduled/background recomputation
- Redis caching for hot company cards
- invalidate/recompute after report verification/status changes

## 8. Audit logging

Mandatory for:
- moderation actions
- verification status changes
- company corrections
- company claims
- evidence access
- user sanctions
- metric override (prefer none)

Append-only audit semantics.

## 9. Abuse prevention

- IP/user rate limits
- signup throttling
- CAPTCHA/challenge only when risk indicates
- duplicate detection
- device/session risk signals within privacy bounds
- report velocity thresholds
- brigading anomaly detection hooks

## 10. Observability

Structured logs, request IDs, error tracking, health endpoints.

Endpoints:
- `/health/live`
- `/health/ready`

Include DB and Redis readiness checks.
