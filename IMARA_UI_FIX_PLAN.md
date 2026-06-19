# Imara UI Fix — Implementation Plan
*How we'll fix the four areas + the bug. Researched patterns, then a file-by-file build plan. Stack: React 18 + Vite + Tailwind. Key finding: `recharts` and `lucide-react` are already in `package.json` but unused — so charts and accessible icons need no new dependencies.*

## Researched implementation patterns (the "how")
- **Accessible SVG charts:** the most screen-reader-reliable pattern is `<svg role="img">` with a `<title>` + `<desc>` referenced via `aria-labelledby`/`aria-describedby`; decorative SVG gets `aria-hidden="true"`; never rely on colour alone — pair every status with icon **and** text; complex charts get a visually-hidden data table fallback ([TPGi](https://www.tpgi.com/using-aria-enhance-svg-accessibility/), [Smashing — accessible SVG patterns](https://www.smashingmagazine.com/2021/05/accessible-svg-patterns-comparison/), [Deque](https://www.deque.com/blog/creating-accessible-svgs/)).
- **Scroll-spy TOC:** `IntersectionObserver` watching the section elements, with `rootMargin` like `-20% 0% -35% 0px`, setting an `activeId` — shorter and faster than scroll listeners ([CSS-Tricks](https://css-tricks.com/table-of-contents-with-intersectionobserver/), [LogRocket](https://blog.logrocket.com/create-table-contents-highlighting-react/)).
- **Recharts:** declarative React/D3 charts; use `ReferenceLine` for benchmarks, theme via our hex tokens, wrap in `ResponsiveContainer` ([LogRocket — React chart libs](https://blog.logrocket.com/best-react-chart-libraries-2026/), [Recharts customize](https://recharts.github.io/en-US/guide/customize/)).
- **Multi-step form:** per-step validation that doesn't bleed across steps, free Back/Forward navigation, and persistence because the flow is long-lived ("Back must not punish progress") — we'll do this with plain React state + `sessionStorage` (no new libs) ([ClarityDev](https://claritydev.net/blog/build-a-multistep-form-with-react-hook-form), [Reform](https://www.reform.app/blog/7-tips-for-multi-step-form-validation)).

## The plan, file by file

### Wave 1 — bug fix + accessibility + navigation (ship first)
1. **Bug:** `App.jsx` — analysis-error path sets `phase` to `'upload'` (not rendered) → change to `'intake'`; tidy the stale `'upload'` reference in `Navbar.jsx`.
2. **Focus + contrast:** `index.css` — add a strong global `:focus-visible` ring (WCAG 2.4.11); lift the lowest-contrast text (`slate-600`→`slate-500`, key `slate-500`→`slate-400`).
3. **Accessible score rings:** `ImaraScoreHero.jsx`, `ScoreCards.jsx` — give each ring `role="img"` + `aria-label` ("Imara Score 44 of 100, Band D, At Risk"); mark the decorative track `aria-hidden`.
4. **Colour-not-alone:** `ScoreCards.jsx`, `FinancialRatios.jsx`, `FindingsList.jsx` — pair every status colour with a lucide icon + text + `aria-label` (e.g. AlertTriangle/CheckCircle).
5. **Button semantics:** add `type="button"` everywhere it's missing.
6. **Section nav:** new `SectionNav.jsx` (IntersectionObserver scroll-spy, sticky right rail on `xl`, hidden below); wire into `Dashboard.jsx` using existing section `id`s; add a back-to-top control.

### Wave 2 — context for the numbers + intake wizard
7. **Explain-this tooltips:** small accessible info buttons (aria-label + title) on the Imara Score, each component, and each score card — plain-language "what this means / what good looks like".
8. **Benchmark cue:** `ImaraScoreHero.jsx` component bars get a faint target tick at the "good" threshold; `FinancialRatios.jsx` keeps its benchmark column but gains a mini bar with a benchmark marker.
9. **Real forecast chart:** `ValuationPanel.jsx` — replace the CSS forecast bars with a Recharts line chart (bull/base/bear trajectory from today's revenue to the 12-month scenarios), built accessibly (role/desc + visually-hidden summary). Valuation range bar stays (already clear).
10. **Intake wizard:** refactor `SmartIntake.jsx` into a 4-step flow (Identity → Financials & Tax → Documents → Context) with a progress bar + step labels, per-step inline validation with friendly messages, Back/Next, and `sessionStorage` persistence so a refresh never wipes progress. All existing fields, upload zones, and the submit payload are preserved exactly.

### Verification
After each wave: `npm run build` must pass; spot-check keyboard focus order and that every status reads as icon+text; confirm the intake still posts the identical multipart payload. Ship via `push_imara.bat`; confirm CI green and Vercel redeploy.
