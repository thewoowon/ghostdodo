# 03. UX, Information Architecture & Screens

## 1. Public routes

```text
/
/search?q=
/companies/[companySlug]
/companies/[companySlug]/ghostory
/companies/[companySlug]/jobs
/dex
/community
/community/[postId]
/jobs
/jobs/[jobId]
/about
/methodology
/policy/reporting
/policy/verification
```

Authenticated:

```text
/me
/me/reports
/me/reputation
/me/saved
/me/applications
/report/new
/report/[id]/edit
/community/new
```

Company representative:

```text
/company-portal
/company-portal/claim
/company-portal/[companyId]
/company-portal/[companyId]/corrections
```

Admin:

```text
/admin
/admin/reports
/admin/evidence
/admin/disputes
/admin/companies
/admin/users
/admin/abuse
```

## 2. Landing page

Order:

1. Minimal header
2. Hero
3. Large company search
4. “오늘의 관측” aggregate strip — only real data
5. Two balanced blocks:
   - 답장이 살아있는 회사
   - 관찰이 필요한 회사
6. GhostDodo 도감 preview
7. How verification works
8. Contributor reputation preview
9. Recent community threads
10. Footer / methodology / policies

If database is empty at launch, do not fake company rankings. Replace with onboarding state explaining that the archive is being built.

## 3. Company search

Autocomplete results:
- Korean legal/company name
- aliases / English name where available
- logo if legitimately sourced or neutral monogram fallback
- industry
- report count
- “표본 부족” state when needed

Support typo-tolerant Korean search and aliases.

## 4. Company detail page

Above the fold:

```text
[company identity]
[save] [share]

Response Rate      Ghost Rate      Median Response
82%                18%             7.4일
n=143 / 최근 12개월

[현재 판정 badge]
```

Then:

### Stage breakdown
- 지원
- 서류
- 코딩/필기
- 과제
- 1차 면접
- 2차/추가 면접
- 최종 면접
- 처우/오퍼

### Ghostory
Chronological aggregated observations. Never expose reporter identity.

### Recent verified observations
Structured cards:
- hiring period
- role category
- stage
- promised date if any
- actual response date or elapsed days
- outcome communication status
- verification status
- helpful votes

### Jobs
Current linked job postings. MVP is deep-link only.

### Company statement
Optional claimed-company response/policy.

### Correction mechanism
Visible `사실관계 정정 요청` link.

## 5. Report submission flow

Make this a calm wizard, not an angry textarea.

### Step 1 — Company
Search/select existing company; request addition if absent.

### Step 2 — Hiring context
- job title free text
- normalized role category
- employment type
- recruitment period / application date
- source job board

### Step 3 — Furthest stage
- application
- document screening
- test/coding
- assignment
- interview 1
- interview 2+
- final interview
- compensation/offer

### Step 4 — Communication timeline
- last interaction date
- company promised a result date? yes/no
- promised date/window
- result received? yes/no
- actual result date
- channel: email/SMS/call/job-board/etc.

### Step 5 — Outcome
- passed
- rejected
- withdrew
- unknown/no disposition

### Step 6 — Evidence (optional but strongly encouraged)
Private upload only.

Allow:
- result email screenshot
- interview invitation
- explicit promised-result-date message
- job-board status screenshot

Before upload: tell users to redact other people’s names, phone numbers, email addresses, IDs.

### Step 7 — Short context
Structured tags first. Optional free text with strict character limit.

### Step 8 — Preview and consent
Explain what becomes public and what remains private.

## 6. GhostDodo 도감 `/dex`

This is the brandable exploration surface.

Views:
- most observed
- best response rate
- longest median response
- interview-stage ghost rate
- recent improving companies
- newly added companies

Use cards with custom SVG species/status marks.

Do not call it Pokédex or imitate Pokémon card layout.

## 7. Community

Community should attach to data rather than become anonymous chaos.

Post types:
- 질문
- 채용 타임라인 공유
- 결과 기다리는 중
- 경험 회고
- 데이터 정정/추가 정보

Company tagging is allowed; personal naming of recruiters/interviewers is prohibited.

## 8. Application deep-link

MVP:
- GhostDodo indexes/accepts job links
- `지원하러 가기` opens original employer/job-board posting
- track outbound click

Later:
- save application
- expected-response reminders
- result tracking
- consented automatic conversion to observation data
