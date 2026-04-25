# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev          # Start dev server (Next.js)
npm run build        # Production build (static export)
npm run lint         # ESLint
npm run type-check   # TypeScript check without emitting
```

No test suite is configured.

## Environment

Copy `.env.local.example` to `.env.local` and fill in:
- `NEXT_PUBLIC_API_URL` — API Gateway base URL (e.g. `https://<id>.execute-api.ap-southeast-2.amazonaws.com/prod`)
- `NEXT_PUBLIC_USER_POOL_ID` — Cognito User Pool ID
- `NEXT_PUBLIC_USER_POOL_CLIENT_ID` — Cognito App Client ID
- `NEXT_PUBLIC_REGION` — AWS region (default: `ap-southeast-2`)

## Architecture

**Static export** — `next.config.ts` sets `output: 'export'`, so the build produces a static site with no server-side rendering. This constrains caching strategies: no `revalidatePath`, no server actions, no route handlers at runtime.

### Auth flow

`app/layout.tsx` wraps everything in `AmplifyProvider` (a `"use client"` component that initialises AWS Amplify once). Auth state lives in Amplify/Cognito; there is no server-side session or middleware guard — all route protection is done client-side inside each page.

`lib/auth.ts` caches the Cognito JWT with a 3-minute expiry buffer. `lib/api.ts` injects the token as `Authorization: Bearer <token>` and retries once on 401 (clearing the cache first).

### Data flow

All data fetching is client-side:
- **SWR** (`GalleryTab`) for list-images with a 30-second dedup interval
- **Plain `fetch` via `lib/api.ts`** for mutations (upload, modify-tags, delete, search)

There is no global state (no Redux/Zustand/Context). State is local to each tab component; the dashboard passes `onResult` callbacks to display results in `ResultsPanel`.

### Route structure

```
app/
  layout.tsx            — root layout, font, AmplifyProvider
  page.tsx              — redirects to /login
  (auth)/
    login/page.tsx      — sign-in
    signup/page.tsx     — sign-up + email confirmation
  dashboard/
    layout.tsx          — authenticated shell (header, sign-out)
    page.tsx            — 6-tab interface
```

### Component / lib split

- `components/` — UI components; most are `"use client"` (tabs, gallery, auth forms, error boundary)
- `lib/api.ts` — single request wrapper; all API endpoints are defined here as named functions
- `lib/auth.ts` — token caching and sign-out
- `lib/amplify-config.ts` — reads `NEXT_PUBLIC_*` env vars and exports the Amplify config object
- `lib/types.ts` — shared TypeScript types (`ImageRecord`, `SearchResult`, etc.)

### Styling

Tailwind CSS v4 with shadcn/ui (base-nova style, lucide icons). Use `cn()` from `lib/utils.ts` for conditional class merging. No CSS modules; all styling is inline Tailwind classes.

### Image handling

Remote images served from S3 (`*.s3.amazonaws.com`). Always use `next/image` — remote patterns are configured in `next.config.ts`. Filenames are derived by splitting the S3 URL on `/` and taking the last segment.

## Key constraints

- **Static export** means `next/headers`, `cookies()`, server actions, and route handlers that run at request time are unavailable.
- All auth and API calls must use `"use client"` components or be invoked from them.
- The API base URL is `NEXT_PUBLIC_API_URL` — never hard-code endpoints; always call the functions in `lib/api.ts`.
