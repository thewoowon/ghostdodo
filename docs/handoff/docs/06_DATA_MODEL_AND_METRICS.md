# 06. Data Model & Metrics

## 1. Core entities

### User
- id
- handle
- auth identity
- role
- reputation_score
- credit_balance
- trust_state
- created_at

### Company
- id
- slug
- legal_name_ko
- display_name_ko
- name_en
- aliases
- industry
- website
- company_size_band
- verification/claim state

### RecruitmentExperience
- id
- user_id (private)
- company_id
- role_title
- role_category
- employment_type
- source
- application_date
- furthest_stage
- outcome
- result_received
- result_received_at
- promised_result
- promised_result_at or promise window
- last_company_interaction_at
- free_context
- verification_status
- created_at

### RecruitmentStageEvent
Allows precise event timeline.
- experience_id
- event_type
- stage
- occurred_at
- channel
- metadata

### Evidence
- id
- experience_id
- object_key
- sha256
- content_type
- size
- pii_review_state
- access_state

### VerificationReview
- report/evidence id
- reviewer
- decision
- reasons
- structured checks
- timestamps

### CompanyMetricSnapshot
- company_id
- window_start/end
- stage filter
- qualified_n
- response_rate
- ghost_rate
- median_response_days
- broken_promise_rate
- verified_ratio
- confidence/eligibility state

### ReputationEvent
Immutable ledger.

### CreditLedger
Immutable credit ledger.

### JobPosting
- company_id
- source_url
- title
- location
- employment_type
- active state
- source
- observed_at

### CommunityPost / Comment / Vote
Standard relations + moderation state.

### CompanyClaim / CorrectionRequest / CompanyStatement
Separate, auditable entities.

## 2. Qualification windows

Do not call an observation “ghosted” immediately.

Store configurable thresholds by stage. Initial product defaults can be conservative and labeled methodology defaults, for example:

- application: longer threshold
- test/assignment: medium threshold
- interview: shorter threshold
- explicit promised date: promise deadline + grace period

**Do not hardcode these values into business logic.** Put them in configuration/versioned methodology.

## 3. Ghost Rate

Conceptual definition:

```text
Ghost Rate = qualified ghost observations / qualified concluded-or-overdue observations
```

Exclude:
- user withdrew before outcome
- observation window not elapsed
- obvious duplicate reports
- rejected/unverified abuse reports
- reports without enough timing information

Display sample size and time window with every rate.

## 4. Response Rate

```text
Response Rate = explicit disposition received / qualified observations
```

A rejection email counts as a successful response.

That principle is central to the product.

## 5. Broken Promise Rate

Among reports where a company communicated a result deadline/window:

```text
Broken Promise Rate = promise missed without updated communication / qualified promised timelines
```

This is more defensible and useful than emotional “ghosting” labels.

## 6. Median response time

For experiences receiving disposition:
- choose stage-specific anchor event
- compute elapsed days to explicit disposition
- use median, not mean
- display p25/p75 later if enough data

## 7. Sample-size protection

Never publish categorical company badges from tiny samples.

States:
- `INSUFFICIENT_DATA`
- `EARLY_SIGNAL`
- `PUBLISHABLE`
- `HIGH_CONFIDENCE`

Thresholds must be methodology-configurable.

Always display `n` and window.

## 8. Recency weighting

Old hiring behavior should fade.

MVP may use simple rolling windows (6m/12m/all-time) rather than opaque weighting.

Preferred default public view: recent 12 months.

## 9. No secret pay-to-win weighting

Company sponsorship, claim status, ad spend, or subscription must never change user report weight or public metric calculation.
