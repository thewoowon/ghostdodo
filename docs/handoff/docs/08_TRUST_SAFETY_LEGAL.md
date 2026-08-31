# 08. Trust, Safety & Korean Launch Guardrails

> Product/engineering guardrails only. Obtain Korean legal counsel before public launch, especially for defamation, privacy, intermediary liability, evidence retention, and dispute procedures.

## 1. Core defensive product design

GhostDodo should publish **structured events and aggregates**, not unrestricted allegations.

Good public record:

```text
2026-08-03 1차 면접
2026-08-10까지 결과 안내 예정
2026-08-31 현재 결과 통보 미수신
검증 상태: Verified
```

Bad public record:

```text
인사팀이 악질이고 지원자를 무시하는 쓰레기 회사
```

## 2. Free-text constraints

- short optional context only
- strong moderation
- block personal names/contact details
- block doxxing
- prohibit speculation about individual motives
- prevent criminal/fraud allegations without appropriate process

## 3. Evidence privacy

Evidence uploads are moderation material, not public posts.

- private object storage
- short-lived signed access
- audit evidence views
- user-facing deletion process subject to retention/legal needs
- strip EXIF where relevant
- detect and redact PII before moderator workflow where feasible

## 4. Reporter privacy

Never disclose reporter identity to a company as the default dispute flow.

Company correction should challenge the **record**, not identify the reporter.

## 5. Right of correction / response

Every company page must expose a correction route.

Workflow:
1. Company submits factual challenge.
2. Moderation reviews source data.
3. Record may be corrected, relabeled, or removed.
4. Audit trail retained internally.
5. Material aggregate changes trigger metric recomputation.
6. Company can publish a bounded official statement.

## 6. Company claims

Require proof of company domain/authority before granting representative status.

Claimed status does not grant report removal rights.

## 7. Anti-brigading

Detect:
- sudden report bursts
- shared text fingerprints
- duplicate evidence hashes
- recently created account clusters
- single-source campaigns

Temporarily exclude suspicious clusters from public aggregates pending review.

## 8. Metric language

Do not present uncertainty as fact.

Always show:
- sample size
- date window
- methodology link
- verification mix

Use `표본 부족` aggressively.

## 9. Personal information

Design for Korea’s Personal Information Protection Act obligations from day one:
- data minimization
- clear purpose
- retention policy
- access/correction/deletion workflows where applicable
- access control and auditability
- privacy policy and consent records

Do not collect resident registration numbers, unnecessary addresses, private recruiter contact data, or sensitive attributes.

## 10. Moderation policy must exist before launch

At minimum:
- prohibited content
- evidence policy
- verification levels
- appeals
- company corrections
- repeat abuse sanctions
- emergency takedown path

## 11. Public launch gate

Do not publicly launch real-company negative rankings until:
- methodology page exists
- report qualification thresholds exist
- correction/dispute flow works
- moderation console works
- privacy policy/terms are reviewed
- sample-size suppression works
- evidence is private
