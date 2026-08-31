# 02. Brand & Visual System

## 1. Brand name

# GhostDodo

Domain: `ghostdodo.com`

Core world:
- ghost = missing response / disappearing communication
- dodo = extinction metaphor
- archive / field research = structured observations

The humor should come from deadpan data language, not from insulting employers.

## 2. Hero copy

### Required first screen

**지원하기 전에, 답은 해주는 회사인지 확인하세요.**

Supporting text:

**답장이 멸종된 회사들을 기록합니다.**  
지원자들이 직접 남긴 채용 응답 기록을 바탕으로 회사별 결과 통보율과 응답 시간을 확인하세요.

Primary CTA: `회사 검색하기`  
Secondary CTA: `내 경험 기록하기`

## 3. Original mascot requirement — mandatory

Claude Code must **not** solve visual design with emoji, Memoji, Twemoji, stock icon packs, or copied illustrations.

Generate a bespoke SVG system directly in the repository.

### GhostDodo mascot

Create an original extinct-bird-inspired mascot that is legally and visually distinct from existing characters.

Characteristics:
- rounded but not babyish
- slightly awkward extinct bird silhouette
- subtle translucent ghost tail or trailing lower body
- distinctive oversized beak geometry
- simple eyes with dry/deadpan expression
- 1–2 signature geometric details that make silhouette recognizable at 24px
- works as outline, filled silhouette, and mono favicon

Do **not** resemble Pokémon, StarCraft Ghost, Duolingo, Angry Birds, or existing commercial mascots.

### SVG asset families

Create hand-authored reusable SVG components:

- `DodoMascotHero`
- `DodoMascotSearch`
- `DodoMascotEmptyState`
- `DodoMascotVerified`
- `DodoMascotExtinct`
- `DodoEgg`
- `FossilMark`
- `FootprintMark`
- `RadarRipple` (generic observational motif, not product name)
- `FieldNotebook`
- `EvidenceStamp`
- `ResponseSignal`
- `SilenceSignal`
- `TimelineBone`
- rank badge shapes

No emoji in primary navigation or metric cards. Small Unicode symbols can exist only in low-priority editorial text if unavoidable.

## 4. Visual direction

The interface should feel like:

**modern Korean consumer web + field guide/archive + slightly absurd extinction museum**

Not:
- beige scrapbook
- children’s game
- neon gamer UI
- corporate HR SaaS dashboard
- generic shadcn clone

### Palette behavior

Choose a restrained palette with:
- near-white warm background
- ink-like near-black type
- one recognizable “Dodo” brand accent
- warning/critical colors used sparingly and semantically
- positive response states visually strong enough to avoid negativity bias

Do not scatter many pastel colors.

### Typography

Korean-first typography. Prefer a high-quality Korean variable sans available by web license / system fallback. Use strong display weight for hero and tabular-number support for metrics.

## 5. Interaction motifs

- Search bar should be the visual anchor of landing page.
- Metric cards use subtle counting / reveal motion.
- Ghostory timeline uses a custom bone/footprint line rather than generic timeline dots.
- When a report is successfully verified, a tiny Dodo “field stamp” animation can appear.
- Avoid gimmicky constant mascot motion.

## 6. Share cards — viral requirement

Generate server-renderable share-card layouts for company pages.

Example:

```text
OO테크
결과 통보율 24%
답장 상태: 멸종위기
최근 6개월 검증 기록 38건
ghostdodo.com
```

Share cards must:
- be visually distinctive
- not contain inflammatory language
- include sample size/time window
- include “verified/unverified mix” if relevant
- look good on KakaoTalk, X, Threads, Instagram stories/screenshots

## 7. Copy vocabulary

Approved playful copy:
- 답장이 멸종된 회사들을 기록합니다.
- 새로운 흔적을 발견하셨나요?
- 도감에 기록하기
- 최근 관측 기록
- Ghostory
- 답장 생존
- 멸종위기
- 관찰 표본이 부족합니다
- 아직 판정하기 이릅니다

Avoid:
- 쓰레기 회사
- 악덕 기업
- 박제
- 조져버리기
- 범죄자처럼 단정하는 표현
