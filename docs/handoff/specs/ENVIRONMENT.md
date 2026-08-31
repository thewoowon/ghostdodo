# Environment & Deployment

## Local development

Recommended services:

```text
web       : localhost:3000
api       : localhost:8000
postgres  : localhost:5432
redis     : localhost:6379
object    : local S3-compatible service or provider dev bucket
```

## `.env.example`

```dotenv
# Web
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# API
APP_ENV=development
APP_BASE_URL=http://localhost:8000
WEB_BASE_URL=http://localhost:3000
DATABASE_URL=postgresql+asyncpg://ghostdodo:ghostdodo@localhost:5432/ghostdodo
REDIS_URL=redis://localhost:6379/0

# Auth
AUTH_SECRET=change_me

# Object storage
S3_ENDPOINT=http://localhost:9000
S3_REGION=auto
S3_BUCKET=ghostdodo-evidence-dev
S3_ACCESS_KEY=change_me
S3_SECRET_KEY=change_me

# Observability
SENTRY_DSN=

# Email
EMAIL_PROVIDER=
EMAIL_FROM=

# Feature flags
ENABLE_COMMUNITY=false
ENABLE_JOBS=false
ENABLE_COMPANY_PORTAL=false
```

## Deployment recommendation

Keep architecture provider-agnostic.

Possible production topology:
- Next.js web: Vercel or container platform
- FastAPI: container service
- PostgreSQL: managed DB
- Redis: managed Redis
- Evidence: private S3-compatible bucket
- CDN for public static assets only

Evidence bucket must not be public.

## CI gates

Web:
- typecheck
- lint
- unit tests
- build

API:
- ruff
- mypy/pyright as selected
- pytest
- alembic migration sanity

Integration:
- boot disposable Postgres/Redis
- apply migrations
- vertical-slice API test
