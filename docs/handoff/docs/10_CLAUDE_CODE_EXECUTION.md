# 10. Claude Code Execution Instructions

## Read this first

Build GhostDodo as a real product, not a static concept demo.

Do not stop after producing screens. Implement the vertical slice end-to-end.

## Mandatory stack

Frontend:
- Next.js 16.3.3+ Active LTS
- App Router
- TypeScript strict
- pnpm

Backend:
- FastAPI
- Python 3.12+
- Pydantic v2
- SQLAlchemy 2.x async
- Alembic
- uv

Infra:
- PostgreSQL
- Redis
- S3-compatible object storage interface
- Docker Compose for local services

## Repository form

Use a monorepo:

```text
ghostdodo/
  apps/
    web/
    api/
  packages/
    shared-types/      # only if genuinely useful
  infra/
    docker-compose.yml
  docs/
  .github/workflows/
  README.md
  .env.example
```

## First-pass implementation order

### 1. Bootstrap
Create web/API/database/cache. Establish migrations, environment validation, linting, formatting, tests, CI.

### 2. Brand system before page sprawl
Create original SVG GhostDodo components. Do not use emoji as mascot/icon substitute.

Create a coherent design-token layer and only then implement screens.

### 3. Domain model
Implement Company, User, RecruitmentExperience, StageEvent, Evidence, VerificationReview, MetricSnapshot, ReputationEvent, CreditLedger.

### 4. Landing/search/company
Implement real database-backed search and company detail. Empty state if there is no seed data.

### 5. Report submission
Implement wizard, validation, drafts, final submit.

### 6. Evidence
Implement signed uploads and private moderation retrieval.

### 7. Moderation
Build admin queue before making report aggregates public.

### 8. Metrics
Implement qualification logic, sample suppression, stage breakdown and Ghostory.

### 9. Reputation
Immutable ledgers and rank rules.

### 10. Community/jobs
Only after the trust/data loop is functional.

## Quality bar

### Product
- Korean copy should feel native, short and precise.
- Humor is dry, not meme spam.
- Positive response behavior gets equal visual treatment.

### Engineering
- no `any` without explicit justification
- typed API client
- domain enums centralized
- transactional writes for report + reputation side effects
- DB indexes for company search/report queries
- no N+1 on company page
- API tests for metric calculations
- frontend tests for report wizard critical path

### Security
- signed uploads
- secure auth/session
- CSRF-aware mutation design where applicable
- strict CORS
- rate limiting
- no secrets in client bundle
- evidence access logs

## Seed data rule

Never invent negative records for actual Korean companies.

For development:
- use fictional companies such as `도도랩`, `철새테크`, `화석소프트`
- mark fixtures as demo

Real company directory metadata may be added later from lawful/verified sources, but public response metrics require actual qualified user data.

## Exact homepage copy to preserve initially

H1:

> **지원하기 전에, 답은 해주는 회사인지 확인하세요.**

Sub-copy:

> **답장이 멸종된 회사들을 기록합니다.**  
> 지원자들이 직접 남긴 채용 응답 기록을 바탕으로 회사별 결과 통보율과 응답 시간을 확인하세요.

Primary CTA: `회사 검색하기`  
Secondary CTA: `내 경험 기록하기`

## Brand implementation commandment

**Do not use Memoji, emoji, generic cartoon sticker packs, or copied game character motifs.**

Create original SVG assets in code. GhostDodo should have a recognizable silhouette and its own field-guide visual language.

## Definition of done for first vertical slice

A new user can:
1. open landing page
2. search a fictional seed company
3. view its no-data/metric state
4. authenticate
5. submit a structured experience
6. privately upload evidence
7. moderator verifies it
8. aggregate metrics recompute
9. company page reflects the verified observation
10. user reputation/credit ledger records the contribution

Do not move to broad feature expansion until this exact loop works.
