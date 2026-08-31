# API Contract — v1 Draft

Base: `/api/v1`

## Companies

```text
GET    /companies/search?q=&cursor=
GET    /companies/{slug}
GET    /companies/{slug}/metrics?window=12m
GET    /companies/{slug}/ghostory?cursor=
GET    /companies/{slug}/reports?verification=verified&cursor=
GET    /companies/{slug}/jobs?cursor=
POST   /companies/request
```

## Reports

```text
POST   /reports
GET    /reports/{id}
PATCH  /reports/{id}
POST   /reports/{id}/submit
DELETE /reports/{id}              # policy-aware soft delete/request
```

### Create report — representative payload

```json
{
  "company_id": "uuid",
  "role_title": "프론트엔드 개발자",
  "role_category": "SOFTWARE_ENGINEERING",
  "employment_type": "FULL_TIME",
  "source": "COMPANY_SITE",
  "application_date": "2026-08-01",
  "furthest_stage": "INTERVIEW_1",
  "last_company_interaction_at": "2026-08-10T05:00:00Z",
  "promised_result": true,
  "promised_result_date": "2026-08-17",
  "result_received": false,
  "outcome": "UNKNOWN",
  "context": "결과 안내 예정일 이후 별도 안내를 받지 못함"
}
```

## Evidence

```text
POST /reports/{id}/evidence/upload-intent
POST /reports/{id}/evidence/{evidenceId}/complete
DELETE /reports/{id}/evidence/{evidenceId}
```

Public report APIs must never return `object_key` or signed evidence URL.

## Me

```text
GET /me
GET /me/reports
GET /me/reputation
GET /me/credits
GET /me/saved-companies
POST /me/saved-companies/{companyId}
DELETE /me/saved-companies/{companyId}
```

## Community

```text
GET  /community/posts?cursor=&company=
POST /community/posts
GET  /community/posts/{id}
POST /community/posts/{id}/comments
POST /community/posts/{id}/helpful
POST /community/comments/{id}/helpful
POST /community/content/{id}/report
```

## Jobs

```text
GET  /jobs?company=&q=&cursor=
GET  /jobs/{id}
POST /jobs/{id}/outbound-click
```

## Company representative

```text
POST /company-claims
GET  /company-portal/{companyId}
POST /company-portal/{companyId}/corrections
POST /company-portal/{companyId}/statement
```

## Admin

```text
GET  /admin/reports?status=
GET  /admin/reports/{id}
POST /admin/reports/{id}/decision
GET  /admin/disputes
POST /admin/disputes/{id}/decision
GET  /admin/abuse/signals
```

## Error envelope

```json
{
  "error": {
    "code": "REPORT_NOT_EDITABLE",
    "message": "검토가 시작된 기록은 직접 수정할 수 없습니다.",
    "request_id": "...",
    "details": {}
  }
}
```

## Public metric response example

```json
{
  "company_id": "...",
  "window": "12m",
  "eligibility": "PUBLISHABLE",
  "qualified_n": 143,
  "verified_ratio": 0.81,
  "response_rate": 0.82,
  "ghost_rate": 0.18,
  "broken_promise_rate": 0.11,
  "median_response_days": 7.4,
  "methodology_version": "2026-09-v1"
}
```
