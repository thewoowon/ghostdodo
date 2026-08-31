# 04. Frontend — Next.js

## 1. Baseline

Use:
- Next.js `16.3.3+` Active LTS
- App Router only
- TypeScript strict mode
- React Server Components by default
- Client Components only for interactive islands
- pnpm workspace

Do not use a second frontend framework.

## 2. Suggested repo layout

```text
apps/
  web/
    app/
      (public)/
      (auth)/
      (company)/
      admin/
      api/              # only thin BFF endpoints if truly needed
    components/
      brand/
      company/
      report/
      community/
      reputation/
      ui/
    lib/
      api/
      auth/
      analytics/
      validation/
      formatting/
    public/
      brand/
    styles/
packages/
  shared-types/
  eslint-config/
  tsconfig/
```

## 3. Data fetching

FastAPI owns business API.

- Server Components fetch read-heavy public data from FastAPI.
- Use explicit cache tags / revalidation for public company pages.
- Mutation flows use typed client wrappers.
- Never place business logic in Next.js route handlers if it belongs in FastAPI.

## 4. UI foundation

A utility/component library can be used for primitives, but final appearance must not look like an untouched component-library demo.

Rules:
- bespoke layout and brand surfaces
- own SVG visual assets
- accessible dialogs/forms
- full keyboard navigation
- proper Korean line breaking
- tabular numerals for metrics

## 5. SEO

Company pages are a growth engine.

Implement:
- dynamic metadata
- canonical URLs
- OpenGraph image generation
- JSON-LD where semantically appropriate
- crawlable company name / metrics / methodology text
- sitemap generation
- robots policy

Never SEO-index private user report detail routes.

## 6. Performance

Targets:
- mobile LCP < 2.5s on realistic network
- CLS < 0.1
- avoid shipping charts library for tiny visualizations
- server-render primary company metrics
- lazy-load community/comments below fold

## 7. Forms

Use schema-derived validation matching backend constraints.

Important UX:
- autosave draft locally
- warn before leaving long report flow
- date inputs must be Korean-friendly
- evidence upload progress + removal
- public/private preview before submit

## 8. Custom SVG architecture

Create React SVG components under:

```text
components/brand/svg/
```

Rules:
- currentColor where practical
- accessible titles when semantic
- decorative SVGs `aria-hidden`
- no huge inline paths duplicated across the tree
- support light/dark-compatible rendering even if MVP launches light-first

## 9. Error states

Brand-consistent custom states:
- no company found
- not enough observations
- API unavailable
- evidence upload failure
- moderation pending

Do not use emoji as the primary illustration.
