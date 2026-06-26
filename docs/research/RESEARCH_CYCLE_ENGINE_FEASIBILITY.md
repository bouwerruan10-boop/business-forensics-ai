# A "research-cycle engine" in Imara — honest feasibility & value read

Analysed 2026-06-24, grounded in (a) what Imara already has and (b) current deep-research-agent practice.

## Bottom line (the honest version)
**Yes it's feasible, and it actually fits Imara's DNA — but only one of the three things people mean by "research engine" is clearly worth building, and it's the least glamorous one.** The biggest mistake would be building a shiny user-facing "research my market" feature: that's more surface area, and Imara's real blockers are *evidence* (Score calibration) and *distribution* (paying users), not features. The version that earns its keep is an **internal corpus-currency engine** that keeps Imara's dated rule data correct — which is a real, recurring, credibility-critical pain today.

## What Imara already has (so this isn't from scratch)
- **Live web research already ships:** `MarketResearchAgent` + `MarketDeepDiveAgent` (SERPER) do brand/market/competitor/news scans; `supplier_live` does live supplier lookups.
- **A verification layer already exists:** `faithfulness.py` + `prose_verifier.py` enforce "numbers computed in code, LLM only narrates, cross-checked" — which is *exactly* the pattern the deep-research literature says is essential: **the verifier must be narrower and more deterministic than the generator.**
- **The pain point is visible in the code:** ~8 dated rule corpora (`sa_rates`, `relocation_tax`, `funder_gates`, `tax_optimizer`, `tax_risk_flags`, `sa_knowledge`, `supplier_catalog`, the benchmark profiles) carry `AS_OF` markers — and at least one already reads **"2024/25" (stale)**. These are hand-maintained and silently rot. Wrong tax/DFI/benchmark numbers = wrong guidance = liability.

So a "research-cycle engine" = an orchestration layer (Plan → Search → Read → Verify → Synthesize) over machinery that's ~60–70% already present.

## Three things "research-cycle engine" could mean — very different ROI

### (A) Internal corpus-currency engine — ★ recommended, build this first
Research that keeps the dated corpora current: fetch authoritative sources (SARS, dtic, DFI sites, StatsSA), detect what changed vs the in-code value, and **propose a sourced diff for human approval** (never auto-write).
- **Problem solved:** the credibility of the whole product rests on these numbers being current; today they rot silently. This turns a manual yearly chore into a semi-automated, **audited** refresh.
- **Fits the DNA perfectly:** research *proposes*, numbers still live in code, a human *disposes* — the "verifier narrower than generator" pattern applied to maintenance. Nothing non-deterministic reaches the report.
- **Cheap:** runs quarterly / at budget time, not per analysis. No per-user cost, no added pipeline latency.
- **Capabilities:** "what changed since AS_OF?" reports per corpus; a PR-style sourced diff; an alert when a figure goes stale; a confidence + citation on each proposed change. Composes with the existing gitleaks/CI + faithfulness machinery.

### (B) Per-analysis claim-grounding engine — selective, medium value / real risk
Ground volatile agent claims (market, news, sector trends) in **live, cited, verified** sources and extend the faithfulness verifier to web claims.
- **Worth it only for the already-volatile market/news section** (which half-exists), **never for the deterministic financial core** — web-grounding the computed figures would *undermine* the moat, not strengthen it.
- **The hard part (and the differentiator):** citation hallucination is the literature's #1 failure — you cannot trust the model to self-cite; you must verify each source is reachable AND actually supports the claim. That citation-verification gate is the real engineering, and it's non-trivial.
- **Costs:** adds web + LLM calls and latency to an already ~11-min, ~25–40-call pipeline → real money at scale; make it opt-in/cached/scoped.

### (C) User-facing on-demand research ("research X for my business") — defer
Competitor pricing, tenders, suppliers, regulatory changes on demand. **Partially exists** (MarketDeepDive, supplier_live).
- **Honest caution:** this is product surface area, and the actual bottleneck is calibration + getting design-partner pilots / paying users. A cool "research" feature doesn't move that needle and adds per-user cost. Expand it only once there's pull from real users.

## Risks to respect (true for any version)
- **Determinism conflict** — live web is non-deterministic and can be wrong; it must never override a computed figure. Cite-or-omit; date + confidence on everything.
- **Citation hallucination / misattribution** — the top failure mode; verify sources, don't trust self-citation.
- **Cascading errors** — a bad research plan poisons every downstream step (DeepHalluBench); gate with the verifier.
- **Liability** — web-sourced tax/legal/financial content feeding guidance must stay non-advice, dated, caveated (the Tax agent's boundary already models this).

## Recommendation
1. **Build (A)** — the corpus-currency engine — first. Highest ROI, lowest risk, aligns with deterministic-first, de-risks the whole product (no more silently-stale numbers), and reuses the SERPER + faithfulness machinery you already have.
2. **(B)** only for the market/news section, and only *with* a genuine citation-verification gate.
3. **Defer (C)** until distribution/pull justifies the surface area.
Framing that keeps Imara honest: **"research proposes, deterministic code + human dispose"** — never "the AI researched it, so the report trusts it."

Sources: Anthropic — multi-agent research system; arXiv surveys on deep-research agents + verification (verifier narrower than generator; cascading planning errors); "Cited but Not Verified" on citation-attribution failure.
