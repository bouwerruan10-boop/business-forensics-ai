# Imara — Next-Phase Strategy
*Written 20 June 2026. Imara is a live, working MVP. This is the analysis of where the leverage now sits and the sequence I'm executing.*

## Where Imara is
Live in production (Railway + Vercel). The recent work made it **trustworthy** (deterministic ratios, faithfulness cross-check, Imara Score with confidence, methodology + data-coverage disclosure), **accessible** (WCAG pass), **navigable** (section nav, intake wizard), and **faster** (specialist wave + tail parallelised: ~46 min → ~10–15 min). The product now *looks and behaves* like something a lender or SME owner could trust.

The remaining gaps are no longer "features" — they are the things that decide whether Imara can run at scale, safely, and economically. Four fronts, in priority order.

## Front 1 — Efficiency (cost & latency) — EXECUTING NOW
A single analysis fires **~40+ Claude calls** (≈20 agents × an `analyze` + a `_parse_findings` JSON call), all on Sonnet, with **no prompt caching**. That is the dominant cost and a big chunk of the latency.
- **Model routing (shipped this commit):** the 2nd call per agent is mechanical JSON extraction — moved to **Haiku 4.5** with a short extraction-only system prompt (was re-sending the full agent persona on Sonnet), with a Sonnet fallback so a model issue never drops findings. Cuts cost on ~half the calls and trims latency on the critical path.
- **Prompt caching (next):** reorder the shared `FINDING_RULES` (injected into every agent) into a common *prefix* and mark it `cache_control` — cache reads cost 0.1× input, and all 40 calls happen within the 5-min TTL window, so 19 of 20 agents read it cached. ([Caching is GA.](https://docs.claude.com/en/docs/build-with-claude/prompt-caching))
- **Structured outputs (later):** [JSON structured outputs](https://docs.claude.com/en/docs/build-with-claude/structured-outputs) can make `analyze` emit validated findings directly, *eliminating the 2nd call entirely* (~20 fewer calls). Bigger refactor; do after caching.

## Front 2 — Reliability
Analysis status lives in an **in-memory dict** (`analysis_status = {}`). A Railway restart mid-run loses the job and its progress; there is no retry and no record. For a paid, multi-minute job this is the biggest robustness risk.
- Persist status/progress to the existing **SQLite** DB so it survives restarts and the polling endpoint reads from it.
- Add **per-analysis cost tracking** (tokens/£ per run) — needed to price the product and watch the Front-1 savings.

## Front 3 — Security & Privacy (POPIA)
Reports contain sensitive financials and are reachable by an **unauthenticated UUID link**; the admin view is ungated. For a tool that itself audits POPIA compliance, this is the sharpest irony and a real exposure.
- **Expiring / revocable** share links; gate the admin dashboard; per-user ownership of analyses.
- This is simultaneously a trust signal and a legal necessity for SA financial data.

## Front 4 — Input robustness
The deterministic engine is only as good as extraction. The earlier CSV bug showed fragility on messy real-world inputs (scanned PDFs, odd layouts).
- LLM **structured extraction** into a validated typed schema (balance-sheet-balances check, source citations) feeding the ratio engine — robust to messy documents. (Pairs naturally with Front 1's structured outputs.)

## Then — GTM & calibration
Commit to the wedge (B2C self-serve vs B2B-to-lenders) and **back-test the Imara Score weights** against real outcomes once there's a dataset. These need real users/data, so they follow the engineering hardening above.

## Sequence I'm executing
1. Efficiency: model routing (now) → prompt caching → structured outputs.
2. Reliability: DB-backed status + cost tracking.
3. Security: expiring links + admin gate + per-user ownership.
4. Input robustness: structured extraction.
Each ships behind a green CI build, the established way.
