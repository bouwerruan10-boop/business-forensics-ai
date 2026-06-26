# Imara UI/UX Improvement Plan
### Deep-dive research → self-questions → researched answers → prioritized plan
*Prepared 19 June 2026. Scope: the Imara React/Vite frontend (`frontend/src`). Method: inventory the live UI, pose the questions a UX reviewer would ask, research each against current (2025–2026) fintech, accessibility, and data-visualization practice, map every finding back to a concrete gap in our code, then prioritize.*

---

## 1. How I approached this

I did not start from opinion. I first read the actual interface — every component in `frontend/src/components`, the routing/state machine in `App.jsx`, the design tokens in `tailwind.config.js`, and the custom CSS/animations in `index.css` — so the recommendations attach to real files, not generic advice. I then turned the observed gaps into ten questions, researched each, and only afterwards wrote the plan below.

**What Imara's UI does well today.** It has a genuinely coherent visual language: a dark navy (`#0D1B2A`) and gold (`#C9A84C`) theme, the Inter typeface, a consistent rounded-card system with subtle borders and tasteful hover states, and a signature element — the **Imara Score™ hero** — that already does several things the research rewards: a single composite number, an A–E band, a transparent weighted component breakdown, and a confidence/completeness indicator. The findings list now carries severity badges plus the new faithfulness "verified / figure unverified" badges, and the analysis-progress screen shows a real agent feed with an honest elapsed/ETA. This is a strong foundation; the plan is about raising it from "good-looking" to "trustworthy, accessible, and effortless."

**The headline gaps I found in the code.** Three stand out before any research: (1) the UI has **essentially zero accessibility affordances** — a repo-wide search found no `aria-*` attributes, no `role`, no `alt`, no `<title>`/`<desc>` on the SVG score rings, and status is carried almost entirely by colour (red/amber/green); (2) there is **no in-page navigation** for a dashboard that stacks nine-plus sections in one long scroll; and (3) the **intake is a single 586-line form** with six upload zones and only asterisk-marked required fields — no step chunking, no progress, no inline validation. I also spotted a small correctness bug: the polling error path in `App.jsx` sets `phase` to `'upload'`, which is not a state the app renders (it should be `'intake'`), so a backend error during analysis leaves the user on a blank screen.

---

## 2. The questions, the research, and how Imara measures up

### Q1. What is the prevailing information hierarchy / progressive-disclosure pattern for finance dashboards in 2025–26?
**Research.** The consensus is "layered": concise summaries up front, details on request, because too much information at once fatigues users; pair this with micro-interactions such as tooltips and hover states to explain complex data points ([ProCreator](https://procreator.design/blog/best-practices-fintech-user-experience/), [Eleken](https://www.eleken.co/blog-posts/fintech-ux-best-practices), [Wildnet Edge](https://www.wildnetedge.com/blogs/fintech-ux-design-best-practices-for-financial-dashboards)).
**Imara today.** The Executive Summary card is a good "layer 1," but below it every section renders at full detail simultaneously — eight score rings, all findings, ratios, credit, valuation, market, compliance, simulator — with no collapsing or "show more." There are almost no tooltips: a new SME owner sees "Efficiency 42" with no way to ask *why* or *what good looks like*.
**Gap.** Add progressive disclosure (collapsible sections, "explain this" tooltips on every score) so the first screen is a digest and depth is one click away.

### Q2. How should a single composite score (credit/health) be visualized for comprehension and trust?
**Research.** Gauge/speedometer styles with red-amber-green bands and a clear pointer are the time-tested convention for score ranges, but the dominant theme in the credit-scoring literature is **transparency** — the reasoning behind the number must be readily available, because opaque scoring methods are resisted by practitioners even when accurate ([ChartExpo](https://chartexpo.com/blog/credit-score-rating-chart), [FasterCapital — credit risk viz](https://fastercapital.com/content/Credit-Risk-Data-Visualization--How-to-Visualize-and-Communicate-Credit-Risk-Data-and-Insights.html)).
**Imara today.** The hero ring + component bars already beat a bare number. What's missing is the "where do I sit on the scale" cue (the ring doesn't show the A–E band thresholds around its circumference) and a plain-language "what would move this score" prompt.
**Gap.** Render the band thresholds on the score arc; add a one-line "biggest lever" beneath the ring (e.g. "Tax compliance is dragging this down the most").

### Q3. Which WCAG 2.2 issues do dark-theme data dashboards most often fail?
**Research.** Colour-alone status is "the most commonly cited accessibility failure in data visualization," and traffic-light red/amber/green indicators are called out specifically — always pair colour with an icon or text label and an `aria-label`. SVG charts are "often inaccessible without deliberate effort" and need `<title>`, `<desc>`, and roles. Putting values only in hover tooltips fails keyboard and screen-reader users. WCAG 2.2 also strengthens focus-appearance (2.4.11) and requires 4.5:1 text contrast / 3:1 for large text ([ADA Compliance Pros](https://www.adacompliancepros.com/blog/accessible-charts), [AIOPSGROUP](https://aiopsgroup.com/accessible-data-visualization/), [Make Things Accessible](https://www.makethingsaccessible.com/guides/contrast-requirements-for-wcag-2-2-level-aa/)).
**Imara today.** This is our single biggest, most concrete deficiency. No `aria`/`role`/`alt` anywhere; score rings are decorative SVG with no `<title>`/`<desc>`; status is colour-first (the text badges like "Critical" help, but the rings and many numbers rely on colour); `slate-500`/`slate-600` body text on navy is likely below 4.5:1; focus styles are minimal (`focus:outline-none` appears without a strong replacement in places); several `<button>`s lack `type`.
**Gap.** A dedicated accessibility pass is the highest-leverage work here — and for a tool whose users include lenders/government programmes, it may be a procurement requirement, not a nicety.

### Q4. How do you design AI-generated results to earn appropriate trust?
**Research.** Explanations drive *trust calibration* — aligning user confidence with actual reliability; interactive explanations build more trust and understanding than static ones; **63% of users are more likely to rely on AI that displays confidence levels** than on black-box answers. But a warning: plausible-looking citations can themselves inflate trust even when wrong, so sources must be real and checkable ([UXmatters](https://www.uxmatters.com/mt/archives/2025/11/the-design-psychology-of-trust-in-ai-crafting-experiences-users-believe-in.php), [NN/g — Explainable AI](https://www.nngroup.com/articles/explainable-ai/), [Springer XAI guidelines](https://link.springer.com/article/10.1007/s10462-025-11363-y)).
**Imara today.** We are ahead of most here — the faithfulness badges and the Score confidence indicator are exactly trust-calibration features. What's underused: findings don't link back to the *source line in the uploaded document* that triggered them, and the confidence signal lives only on the hero, not on individual findings or the sub-scores.
**Gap.** Surface "based on: Bank Statement, p.3" provenance on findings; carry a confidence/uncertainty cue down to section level; make the verification note interactive (click to see computed vs claimed side by side).

### Q5. How do you stop users abandoning a long intake form?
**Research.** The numbers are dramatic: properly segmented multi-step forms outperform single-page equivalents by ~**296%** on average; **27% of users abandon forms that simply look too long**; inline validation cuts errors ~22% and completion time ~42% and lifts satisfaction ~31%; real-time progress indicators + step microcopy drive large conversion lifts ([Amra & Elma stats](https://www.amraandelma.com/multi-step-form-abandonment-stats/), [Webstacks](https://www.webstacks.com/blog/multi-step-form), [Reform — validation](https://www.reform.app/blog/7-tips-for-multi-step-form-validation)).
**Imara today.** `SmartIntake.jsx` is one 586-line page with four sections and six upload zones shown at once — the exact "looks too long" trigger. Required fields are marked only with a gold asterisk; there's no inline validation, no step progress, no save/resume. For a stressed SME owner gathering financials, this is the most likely point of drop-off in the entire funnel.
**Gap.** Convert to a stepped wizard (Identity → Financials & Tax → Documents → Context) with a progress bar, per-step inline validation, and persistence so a half-finished intake survives a refresh.

### Q6. What's the right UX for a multi-minute processing wait?
**Research.** For 10s+ waits show a progress bar, percentage, and status updates; **stream/reveal partial results as they're ready** rather than waiting for 100%; keep the bar always moving (stalls feel broken); visibly communicating progress can cut abandonment by up to ~30%; skeleton screens make loads feel 20–30% faster ([Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/designing-better-loading-progress-ux/), [Onething — skeletons](https://www.onething.design/post/skeleton-screens-vs-loading-spinners), [Psychology of Waiting](https://medium.com/design-bootcamp/the-psychology-of-waiting-in-ux-0f0b24cdeb8f)).
**Imara today.** The progress screen is already solid (live agent feed, honest ETA, shimmer bar). Two gaps remain: the analysis can run many minutes yet the user must keep the tab open with nothing to do, and the dashboard appears all-at-once on completion rather than streaming as agents finish. There's no "email me when it's done."
**Gap.** Stream partial results (show the Executive Summary / Score the moment Phase 1 completes, fill sections as agents finish), add skeleton placeholders, and offer a notify-on-completion option so users can leave.

### Q7. How should the financial data itself be visualized?
**Research.** Keep visuals clean; use **sparklines** — small inline trend charts next to a KPI — to show 12-month context without clutter; always include **benchmark/industry comparison** so a number is read relative to expectation; modern KPI cards now embed sparklines, reference labels, and sub-values ([Julius AI — finance viz](https://julius.ai/articles/data-visualization-finance-industry), [Quadratic](https://www.quadratichq.com/blog/financial-data-visualization-for-modern-finance-teams), [EPC Group — Power BI cards](https://www.epcgroup.net/power-bi-kpi-visuals-dashboard-guide-2026)).
**Imara today.** There is **no charting library in use** — every visual is a hand-rolled SVG ring or a CSS bar. The valuation range, the bull/base/bear forecast, and the financial ratios are shown as static numbers or single bars with no trend and no visible benchmark marker, even though the backend already computes industry benchmarks. A ratio like "Current ratio 1.5x" means little to an SME without "industry median 1.8x" beside it.
**Gap.** Introduce a light chart layer (e.g. Recharts), render the forecast as a scenario line/area chart and the valuation as a range bar, and put a benchmark tick-mark on every ratio and on the Score component bars.

### Q8. How do users navigate a long, multi-section report?
**Research.** Sticky headers increase discoverability and measurably speed task completion; a sticky **table of contents that highlights the current section** gives orientation and scroll feedback; include back-to-top links; lay content in scannable, whitespace-separated zones ([NN/g — Table of Contents](https://www.nngroup.com/articles/table-of-contents/), [Smashing — sticky menus](https://www.smashingmagazine.com/2023/05/sticky-menus-ux-guidelines/)).
**Imara today.** The dashboard renders ~9 stacked `Section`s with no way to jump between them — the user scrolls the entire report to reach, say, SA Compliance or the Simulator. The `Navbar` is the only persistent element and it doesn't expose section anchors.
**Gap.** Add a sticky side (desktop) / collapsible top (mobile) section nav with scroll-spy highlighting and a back-to-top control.

### Q9. What breaks on mobile for data-dense dashboards?
**Research.** Position priority content for F/Z scan patterns and use whitespace/grouping into scannable zones; data tables need deliberate responsive patterns to avoid overflow ([Excited.agency — dashboard UX](https://excited.agency/blog/dashboard-ux-design), [Pencil & Paper — data tables](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables)).
**Imara today.** Responsive intent exists (37 `sm:`, 10 `lg:` utilities) but the score grid scales to `xl:grid-cols-8` — eight rings in a row is cramped on smaller laptops and the `grid-cols-2` mobile fallback puts two rings per row with tight labels. Findings expand into multi-field grids that can feel dense on a phone.
**Gap.** Re-tune the score grid (cap at 3–4 across, let the hero dominate), and verify the findings/ratios layouts on a 375px viewport.

### Q10. What design signals specifically build credibility for a funding-facing tool?
**Research.** Trust in financial products is built through clarity, security cues, and transparency, and — importantly — **interaction quality matters more than time spent**; a single high-quality, transparent session can establish trust ([Eleken](https://www.eleken.co/blog-posts/fintech-ux-best-practices), [ScienceDirect — trust in AI agents](https://www.sciencedirect.com/science/article/pii/S2444569X25001155), [Tandfonline — transparency & trust](https://www.tandfonline.com/doi/full/10.1080/0144929X.2025.2533358)).
**Imara today.** The brand and the Score™ convey authority; the faithfulness layer conveys honesty. Under-leveraged: an explicit "what we could *not* verify / what's missing" panel (which paradoxically raises trust), consistent provenance, and visible methodology ("how the Imara Score is calculated") that a skeptical lender can inspect.
**Gap.** Add a short, linkable "Methodology & data coverage" disclosure and a "limitations of this analysis" note — turning transparency into a credibility asset.

---

## 3. Prioritized improvement plan

Sequenced by impact-to-effort. Each item names the files it touches so it can be picked up directly. "Impact" is on user trust/comprehension/completion; "Effort" is rough frontend build size.

| # | Improvement | Why (research) | Primary files | Impact | Effort |
|---|---|---|---|---|---|
| **P0 — correctness & quick wins** |
| 0.1 | Fix the error-phase bug (`'upload'` → `'intake'`) + add a visible error state on the analysing screen | broken state = total trust loss | `App.jsx` | High | XS |
| 0.2 | Add real focus-visible styles + `type="button"` on all buttons | WCAG 2.4.11; Q3 | `index.css`, all components | Med | S |
| **P1 — accessibility pass (highest leverage)** |
| 1.1 | Pair every colour status with icon+text and `aria-label`; stop conveying state by colour alone | Q3 — #1 dashboard failure | `ScoreCards`, `ImaraScoreHero`, `FindingsList`, `CreditReport` | High | M |
| 1.2 | Give score-ring SVGs `role="img"` + `<title>`/`<desc>` (e.g. "Imara Score 44 of 100, Band D") | Q3 — SVG semantics | `ImaraScoreHero`, `ScoreCards` | High | S |
| 1.3 | Audit & fix text contrast (raise `slate-500/600` on navy to ≥4.5:1) | Q3 — SC 1.4.3 | `tailwind.config.js`, `index.css` | High | S |
| 1.4 | Ensure any hover-only info is also keyboard/SR reachable | Q3 | `FindingsList`, tooltips | Med | M |
| **P2 — navigation & progressive disclosure** |
| 2.1 | Sticky section nav with scroll-spy + back-to-top | Q8 | new `SectionNav.jsx`, `Dashboard.jsx` | High | M |
| 2.2 | Collapsible sections + "explain this" tooltips on every score/metric | Q1, Q2 | `Dashboard`, `ScoreCards`, `ImaraScoreHero`, `FinancialRatios` | High | M |
| 2.3 | Band thresholds on the Score arc + "biggest lever" line | Q2 | `ImaraScoreHero` | Med | S |
| **P3 — trust & explainability depth** |
| 3.1 | Finding provenance ("based on: Bank Statement p.3") | Q4 | `FindingsList`, backend finding schema | High | M |
| 3.2 | Carry confidence cue to section/sub-score level; make verification note interactive (computed vs claimed) | Q4 | `ScoreCards`, `FindingsList` | Med | M |
| 3.3 | "Methodology & data coverage" + "what we couldn't verify" disclosure | Q10 | new `MethodologyNote.jsx`, `Dashboard` | Med | S |
| **P4 — data visualization upgrade** |
| 4.1 | Add a light chart layer (Recharts); forecast → scenario area chart, valuation → range bar | Q7 | `ValuationPanel`, new `ForecastChart.jsx` | High | M |
| 4.2 | Benchmark tick-marks on ratios and on Score component bars (backend already has benchmarks) | Q7 | `FinancialRatios`, `ImaraScoreHero` | High | M |
| 4.3 | Sparklines on KPI cards where any time series exists | Q7 | `ScoreCards`, `FinancialRatios` | Med | M |
| **P5 — intake conversion** |
| 5.1 | Convert `SmartIntake` to a 4-step wizard with progress bar + step microcopy | Q5 — ~296% lift potential | `SmartIntake.jsx` (refactor) | High | L |
| 5.2 | Inline per-step validation with friendly errors | Q5 — −22% errors, −42% time | `SmartIntake.jsx` | High | M |
| 5.3 | Persist intake (sessionStorage) so a refresh doesn't wipe progress | Q5 | `SmartIntake.jsx` | Med | S |
| **P6 — the wait experience** |
| 6.1 | Stream partial results — show Exec Summary + Score as soon as Phase 1 finishes, fill sections as agents complete | Q6 — biggest perceived-speed win | `App.jsx`, `Dashboard`, backend status payload | High | L |
| 6.2 | Skeleton screens for dashboard sections while streaming | Q6 — +20–30% perceived speed | `Dashboard`, new `Skeleton.jsx` | Med | M |
| 6.3 | "Notify me when ready" (email) so users can close the tab | Q6 | `AnalysisProgress`, backend | Med | M |
| **P7 — mobile polish** |
| 7.1 | Re-tune score grid (cap 3–4 across; hero dominant) and verify findings/ratios at 375px | Q9 | `ScoreCards`, `Dashboard`, `FindingsList` | Med | M |

### Suggested sequencing
**Wave A (this week):** P0 (all) + P1 (accessibility). These are correctness and compliance, low-to-medium effort, and the accessibility work is genuinely the highest-leverage quality lift — it also protects against a lender/government procurement blocker.
**Wave B:** P2 (navigation + progressive disclosure) + P3.3 (methodology note) — fast, high-visibility usability gains on the existing report.
**Wave C:** P4 (charts/benchmarks) + P3.1–3.2 (provenance/confidence depth) — turns the report from "numbers" into "contextualized, sourced insight."
**Wave D:** P5 (intake wizard) and P6 (streaming/skeletons/notify) — the two larger builds that lift funnel completion and tame the multi-minute wait; pair P6.1 with the Phase-2 parallelization already shipped.
**Wave E:** P7 mobile polish and final WCAG re-test.

### How we'll verify it worked
Run an automated accessibility check (axe / Lighthouse) before and after Wave A and target zero critical violations + AA contrast; spot-check keyboard-only and screen-reader navigation of the dashboard; and (once analytics exist) watch intake completion rate and time-to-first-meaningful-paint on the report after Waves D. The existing eval/CI discipline applies — ship each wave behind a green build.

---

## 4. The one-paragraph version
Imara already looks credible and, with the Score™, faithfulness badges, and confidence indicator, is ahead of most AI tools on *trust signalling*. The biggest, most concrete gaps are not aesthetic: the interface is **not accessible** (colour-only status, no ARIA/semantics on SVG charts, thin contrast and focus styles — the most-failed items in WCAG dashboard audits), it gives users **no way to navigate or progressively explore** a long report, its **financial numbers lack the trend and benchmark context** that make them meaningful, and its **single long intake form is the funnel's likeliest drop-off** point. Fixing accessibility and report navigation first (fast, high-leverage), then adding benchmark-aware charts, finding provenance, a stepped intake, and streamed results, would move Imara from a polished prototype to a tool a skeptical lender or SME owner can use confidently — and one that meets the accessibility bar such users increasingly require.

---

## Sources
- ProCreator — Fintech UX best practices: https://procreator.design/blog/best-practices-fintech-user-experience/
- Eleken — Fintech UX best practices (trust & simplicity): https://www.eleken.co/blog-posts/fintech-ux-best-practices
- Wildnet Edge — Fintech dashboard UX: https://www.wildnetedge.com/blogs/fintech-ux-design-best-practices-for-financial-dashboards
- ChartExpo — credit score rating chart: https://chartexpo.com/blog/credit-score-rating-chart
- FasterCapital — credit risk data visualization: https://fastercapital.com/content/Credit-Risk-Data-Visualization--How-to-Visualize-and-Communicate-Credit-Risk-Data-and-Insights.html
- ADA Compliance Pros — accessible charts: https://www.adacompliancepros.com/blog/accessible-charts
- AIOPSGROUP — accessible data visualization: https://aiopsgroup.com/accessible-data-visualization/
- Make Things Accessible — WCAG 2.2 AA contrast: https://www.makethingsaccessible.com/guides/contrast-requirements-for-wcag-2-2-level-aa/
- UXmatters — design psychology of trust in AI: https://www.uxmatters.com/mt/archives/2025/11/the-design-psychology-of-trust-in-ai-crafting-experiences-users-believe-in.php
- NN/g — Explainable AI: https://www.nngroup.com/articles/explainable-ai/
- Springer — user-centered XAI design guidelines: https://link.springer.com/article/10.1007/s10462-025-11363-y
- Amra & Elma — multi-step form abandonment stats: https://www.amraandelma.com/multi-step-form-abandonment-stats/
- Webstacks — multi-step form best practices: https://www.webstacks.com/blog/multi-step-form
- Reform — multi-step form validation: https://www.reform.app/blog/7-tips-for-multi-step-form-validation
- Smart Interface Design Patterns — loading/progress UX: https://smart-interface-design-patterns.com/articles/designing-better-loading-progress-ux/
- Onething — skeleton screens vs spinners: https://www.onething.design/post/skeleton-screens-vs-loading-spinners
- Psychology of Waiting (Bootcamp): https://medium.com/design-bootcamp/the-psychology-of-waiting-in-ux-0f0b24cdeb8f
- Julius AI — data visualization in finance: https://julius.ai/articles/data-visualization-finance-industry
- Quadratic — financial data visualization: https://www.quadratichq.com/blog/financial-data-visualization-for-modern-finance-teams
- EPC Group — Power BI KPI visuals & cards: https://www.epcgroup.net/power-bi-kpi-visuals-dashboard-guide-2026
- NN/g — Table of Contents design: https://www.nngroup.com/articles/table-of-contents/
- Smashing Magazine — sticky menus UX: https://www.smashingmagazine.com/2023/05/sticky-menus-ux-guidelines/
- Excited.agency — dashboard UX: https://excited.agency/blog/dashboard-ux-design
- Pencil & Paper — enterprise data tables: https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables
- ScienceDirect — trust in AI-powered agents: https://www.sciencedirect.com/science/article/pii/S2444569X25001155
- Taylor & Francis — transparency & trust in AI: https://www.tandfonline.com/doi/full/10.1080/0144929X.2025.2533358
