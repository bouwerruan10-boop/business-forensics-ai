# Imara Frontend Resilience Audit — the 5-point "users hit a wall and leave" checklist

Audited 2026-06-23 against the React frontend. **Unlike the API/perf checklists, this one is mostly actionable** — Imara's resilience work has been backend-heavy, so the browser app has real gaps. One point is already done well.

| # | Point | Imara today | Verdict |
|---|---|---|---|
| 1 | One component errors → white screen of death | **No error boundary** anywhere | ⚠️ **P0 — real gap** |
| 2 | Loading states: frozen / infinite spinner; no error/empty | loading+error+empty exist, but **no retry, no skeletons** | ⚠️ P1 — partial |
| 3 | Form loses all data on submit failure | **sessionStorage persistence** of all 14 fields | ✅ Already strong |
| 4 | Bugs invisible until a 1-star review | **No client-side error tracking** (backend has Sentry) | ⚠️ P1 — real gap |
| 5 | Dead links / broken images / no 404 | Unknown routes silently fall through; no 404; no img fallback | ⚠️ P2 — minor gap |

## 1 — No error boundary ⚠️ P0 (highest value)
`src/main.jsx` renders `<App/>` inside `<StrictMode>` only — **no error boundary** (0 matches for `ErrorBoundary`/`componentDidCatch`/`react-error-boundary`). So a render error in *any* component (a panel, the dashboard, a chart) takes down the **entire app to a blank white screen** with no message and no recovery. This is the classic "user assumes it's broken and leaves." **Fix:** wrap `<App/>` (and ideally each major section/panel) in an error boundary with a friendly fallback ("Something went wrong — try again") + a reset button. Use either `react-error-boundary` (small lib, `FallbackComponent` + `resetErrorBoundary`) or a zero-dependency class component; if we add Sentry (#4), its `Sentry.ErrorBoundary` does both jobs at once.

## 2 — Async states ⚠️ P1 (partial — the good news: 3 states already exist)
The data panels (`FundingFit`, `FunderGates`, `OwnerRisk`, `InsuranceCession`, `ActionSimulator`, `AskImara`) **already handle loading + error + empty** states (e.g. `if (error) … if (!data) … if (!data.available) …`). What's missing: **(a) no retry button** — an error is a dead end (the user must hard-refresh), and **(b) no skeleton loaders** — loading is plain text ("Working out…"), which on a slow call reads as frozen. **Fix:** add a "Try again" button to each error state that re-triggers the fetch, and replace text-loading with a lightweight skeleton/shimmer.

## 3 — Form resilience ✅ already strong (no action)
`SmartIntake.jsx` persists **all 14 fields to `sessionStorage` on every change** and restores them on mount, and `App.startAnalysis`'s catch sets the error + returns to intake **without clearing state**. So a failed submit (or a refresh, or the back button) does **not** lose the user's input — exactly what the checklist asks for. Already done.

## 4 — No client-side error tracking ⚠️ P1
The **backend** has Sentry (`sentry-sdk`, dormant until `SENTRY_DSN`), but the **frontend has none** (`@sentry/react` absent; no `Sentry.init`). So browser crashes, render errors, and unhandled promise rejections are **invisible to you** — you only find out via user complaints. **Fix:** add `@sentry/react`, init in `main.jsx` with `dsn: import.meta.env.VITE_SENTRY_DSN` (dormant until the env var is set, mirroring the backend pattern; Sentry DSNs are public-safe), and use `Sentry.ErrorBoundary` to satisfy #1 + #4 together. Then crashes arrive with a full stack trace.

## 5 — No custom 404 / broken-asset handling ⚠️ P2 (minor)
Unknown hash routes (`#/nonexistent`) **silently fall through** to the intake form — no NotFound view, so a mistyped/stale link looks like the home page rather than "not found." And there's **no `img onError` fallback** (0 matches), so a broken image renders the browser's broken-icon. (The Vercel `/(.*) → /index.html` rewrite is correct SPA behaviour; the gap is *inside* the SPA router.) **Fix:** a small `NotFound` view rendered for unrecognised routes + an image-error fallback where images are used.

## Prioritised actions
| Priority | Item | Effort | Note |
|---|---|---|---|
| **P0** | Error boundary + friendly fallback + reset | Small | Prevents white-screen-of-death; biggest UX save |
| P1 | Frontend Sentry (`@sentry/react`, dormant until DSN) | Small | You hear about crashes; pairs with #1 via Sentry.ErrorBoundary |
| P1 | Retry buttons on each error state + skeleton loaders | Small-med | Turns dead-end errors into recoverable ones |
| P2 | NotFound view for unknown routes + img onError fallback | Small | Polish; SPA-internal 404 |
| — | Form resilience (#3) | — | Already done — no action |

**Bottom line:** this checklist lands harder than the API/perf ones because frontend resilience was under-invested. The single highest-value fix is the **error boundary** (P0) — ideally added together with **frontend Sentry** (P1) so one change both prevents the white screen *and* reports the crash. Retry/skeletons and a 404 view round it out; form resilience is already handled.

## Update — implemented (2026-06-23, v1.89)

- **#1 Error boundary — DONE.** Zero-dependency `ErrorBoundary` class component wraps `<App/>` in `main.jsx`; friendly fallback ("Something went wrong") with **Try again** (reset) + **Reload page**. Sentry-ready (`window.Sentry.captureException` hook for when #4 is added). No more white-screen-of-death.
- **#2 Async states — DONE (retry + skeleton).** Added a **Try again** button to the error state of the data panels (FundingFit, FunderGates, OwnerRisk, InsuranceCession) — re-triggers the fetch via a `tries` counter — and replaced text loading with a reusable `Skeleton` shimmer.
- **#3 Form resilience — already done** (sessionStorage persistence). No change.
- **#4 Frontend Sentry — DEFERRED (rationale):** needs a dependency + a CSP `connect-src` change (the now-ENFORCING CSP would block Sentry's ingest) + a DSN, and Imara is operator-run so Ruan sees crashes directly. The error boundary is **Sentry-ready** (one-line wire-up). Revisit at the B2C/multi-user pivot when real end-user crashes are invisible.
- **#5 Custom 404 — DONE.** `NotFound` view renders for unrecognised hash routes (was silently falling through to the intake form); "Go to Imara" resets home. (Broken-image `onError` fallback deferred — the app uses inline SVG/charts, near-zero `<img>` surface.)

Verified: production `vite build` clean (2338 modules). Zero new dependency.
