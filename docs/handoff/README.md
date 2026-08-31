# GhostDodo — Claude Code Product/Engineering Handoff

**Domain:** `ghostdodo.com`  
**Primary market:** South Korea  
**Product type:** Recruitment communication transparency + community + application discovery  
**Frontend:** Next.js 16.3.3+ Active LTS, React, TypeScript  
**Backend:** FastAPI, Python 3.12+, Pydantic v2, SQLAlchemy 2.x  
**Primary DB:** PostgreSQL  
**Cache / rate-limit / queues:** Redis  
**Object storage:** S3-compatible  
**Package managers:** pnpm (web), uv (api)

---

## One-line product definition

> **지원하기 전에, 답은 해주는 회사인지 확인하세요.**

GhostDodo is a Korean recruitment transparency platform that records how companies communicate with applicants: whether results were delivered, how long they took, at which hiring stage communication stopped, and how reliably those reports are verified.

The brand world is built around the absurd but memorable idea that **“답장이 멸종된 회사들을 기록합니다.”**

This is not a rage board or blacklist. It is a **structured, evidence-aware recruitment communication database** with community, reputation, and later a job-application loop.

---

## Critical product principles

1. **Facts over insults.** Record events, dates, stages, promises, and outcomes—not defamatory free-form accusations.
2. **Reward verification, not negativity.** Reputation must increase for useful, accurate, corroborated data regardless of whether the company behaved well or badly.
3. **Positive companies matter.** GhostDodo must surface high-response employers as prominently as poor-response employers.
4. **Korean-first.** Korean copy, Korean hiring stages, Korean company search conventions, Korean job-board links, Korean moderation and privacy requirements.
5. **Brand-own every visual.** Do **not** use Apple Memoji, stock emoji, generic emoji illustrations, Pokémon-like assets, StarCraft assets, or copied mascot styles. Build an original GhostDodo visual system using bespoke SVG assets.
6. **Mobile-first web, desktop excellent.** No native app for MVP.
7. **Do not fake data.** Demo data must be clearly marked as sample/demo. Never display invented real-company ghost rates.

---

## Mandatory first build target

Ship a coherent MVP containing:

- Landing page with brand-defining hero
- Company search/autocomplete
- Company detail page
- Structured recruitment-experience submission flow
- Evidence upload flow (private, not public)
- Verification status
- Ghost Rate / Response Rate / response-time metrics
- Ghostory timeline
- “GhostDodo 도감” exploration page
- User profile + reputation + Dodo Credit
- Basic community feed/comments
- Authentication
- Admin/moderation console
- Company correction/response request flow
- Job posting links with “지원하러 가기” deep-link
- SEO-friendly public company pages

Read all files in `/docs` and `/specs` before writing production code.

---

## File map

- `docs/01_PRODUCT_VISION.md` — product thesis, positioning, scope
- `docs/02_BRAND_AND_VISUAL_SYSTEM.md` — GhostDodo world, original SVG system
- `docs/03_UX_IA_AND_SCREENS.md` — IA, routes, screen behavior
- `docs/04_FRONTEND_NEXTJS.md` — frontend architecture and standards
- `docs/05_BACKEND_FASTAPI.md` — backend architecture and service boundaries
- `docs/06_DATA_MODEL_AND_METRICS.md` — schema, metrics, scoring
- `docs/07_REPUTATION_COMMUNITY.md` — credits, reputation, community
- `docs/08_TRUST_SAFETY_LEGAL.md` — anti-abuse, privacy, moderation, Korean launch guardrails
- `docs/09_ROADMAP_ACCEPTANCE.md` — milestones and acceptance criteria
- `docs/10_CLAUDE_CODE_EXECUTION.md` — exact implementation sequence
- `specs/API_CONTRACT.md` — API contract
- `specs/ENVIRONMENT.md` — env variables/deployment

---

## North-star loop

```text
회사 발견
  ↓
GhostDodo에서 회사 검색
  ↓
응답 기록 / Ghostory / Ghost Rate 확인
  ↓
채용공고 확인
  ↓
지원하러 가기
  ↓
내 지원 추적
  ↓
결과 수신 / 미수신 기록
  ↓
검증 가능한 데이터 축적
  ↓
회사 지표 개선
  ↺
```

This loop is the long-term moat.
