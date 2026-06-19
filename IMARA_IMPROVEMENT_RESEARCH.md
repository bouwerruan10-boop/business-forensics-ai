# Imara — Improvement Research, Analysis & Plan
_Compiled 2026-06-19. A self-directed research → analysis → plan cycle._

---

## PART A — Inventory: everything built this engagement

**Features shipped (all live on `main`, CI green):**
- **Imara Score&#8482;** — weighted 0&#8211;100 composite (8 components, re-normalised), A&#8211;E bands, a **confidence/completeness** indicator, single-source band colour, profitability anchored on computed fundamentals.
- **Repaired 4 corrupted agent classes** — FraudDetection, CreditReadiness, Valuation, Forecast (lost to an earlier Edit-tool truncation committed to HEAD); removed a duplicate `ALL_AGENTS`.
- **Deterministic financial-ratio engine** — extracts line items, computes margins / liquidity / gearing / working-capital days, each traceable to source figures; renders a "Financial Fundamentals" panel in dashboard/PDF/HTML.
- **Report integration** — Imara Score + fundamentals in the React dashboard, the PDF (3 audiences) and the HTML report.
- **CI + tests** — GitHub Actions (compile, import app, pytest, frontend build); 19 no-API tests.
- **Resilience & scoring robustness** — every agent phase wrapped in try/except; per-category sub-score cap.
- **Security** — CORS restricted to the Vercel domain + previews + localhost; optional `X-API-Key`; `/api/health` exposes the deploy commit.

**Bugs found & fixed (most surfaced by the live test):**
1. Corrupted `specialist_agents.py` (broke production import) — repaired.
2. `_wrap_flowables` undefined — PDF export 500'd on any real report — defined.
3. `client.js` used a relative `/api`, never `VITE_API_URL` — the deployed frontend **never reached the backend** — wired.
4. `benchmarks.json` was gitignored — missing from every Railway build — committed (CI caught it).
5. Parser emitted an opaque dict-repr — ratio extraction returned empty AND the LLMs hallucinated (gross margin 21.3% vs real 33.2%) — parser now emits clean "label: value" text.
6. Invalid `ANTHROPIC_API_KEY` in Railway — blocked the live run — corrected.
7. Progress UI hard-coded 12 agents + a fake "3&#8211;8 min" ETA — now shows all 20 agents + a real elapsed/estimate.

**Validated by a full live production test** (Imara Score 44 / Band D, 72 findings, all 17+ agents, statute-referenced SA tax findings, live competitor data). An investor briefing PDF was produced.

**Known weaknesses (the targets of this research):**
- **Performance** — ~46 minutes per analysis (sequential agents, 2 LLM calls each, no caching).
- **Extraction robustness** — the parser is regex-on-clean-text; messy PDFs / scans / multi-column statements will still break it (garbage-in risk).
- **No faithfulness check** — AI-cited numbers can still drift; nothing rejects a figure not traceable to source.
- **No evaluation harness** — output *quality* is unmeasured; prompt changes are unguarded for quality.
- **No observability** — no per-agent / per-analysis cost, latency or token tracking.
- **Reliability** — `analysis_status` and the rate-limiter are in-memory: lost on restart, broken beyond one replica.
- **Security / privacy** — confidential SME financials behind an unguessable UUID; no auth/multi-tenancy.
- **Uncalibrated scoring** — Imara Score weights are reasoned, not back-tested.
- **Bespoke orchestration** — a hand-written pipeline (fine today; harder to observe/retry/scale).

---

## PART B — Research findings (with sources)

**B1 · Multi-agent orchestration & evaluation.** The field consolidated in 2025&#8211;26: **LangGraph** (largest production footprint, stateful multi-agent, observability via LangSmith), **CrewAI** (great prototyping ergonomics, weaker production observability/error-recovery), and **Anthropic's Claude Agent SDK** (native tool-use, subagents, hooks, MCP). The repeated production differentiator is **"evaluation infrastructure with regression tests and trace replay"** and human-checkpoint design — framework choice "matters only at the margin."

**B2 · Financial-document extraction.** Modern practice has moved past plain OCR to **LLM structured extraction**: layout-aware reading of income statements / balance sheets directly from PDFs (even image-based), output into a typed schema, with **source-linked citations** and **automated validation checks** (e.g. "does the balance sheet balance?", flag inconsistencies). This is exactly the class of upgrade Imara's weak parser needs.

**B3 · Observability for LLM apps.** The standard is now **tracing** every LLM/tool/retrieval call with token, cost and latency, filterable by user/session/cost/latency. **Langfuse** (open-source) is purpose-built, async/non-blocking, and **OpenTelemetry**-native (the converging telemetry standard). Cost/latency/quality dashboards + alerts are table stakes.

**B4 · The South African SME lending market (the demand case).** SA FinTech lending/BNPL is ~US$980M; the Sub-Saharan SME financing gap exceeds **US$331B** (IFC). **85.6%** of SA funding applications come from micro-enterprises (<R1M turnover) that create **80.5%** of jobs yet are routinely declined because lenders use **outdated consumer-grade scoring**. AI + alternative data is delivering **30&#8211;40% lower default rates**. Incumbents (Lulalend/Lula, $35M Series B; embedded in Vodacom/Yoco/Takealot) are **lenders**, not diagnostic/bankability layers.

---

## PART C — Analysis: questions asked of the research, and answered

**Q1. Adopt an orchestration framework (LangGraph etc.) or keep the bespoke pipeline?**
*Answer:* Keep bespoke **now**. The immediate wins (parallelism, structured outputs, caching) are achievable in the existing FastAPI code at far lower risk than a rewrite. Re-evaluate **LangGraph** only once we need stateful retries, human checkpoints, and built-in trace/eval at scale — and let observability (B3) be the bridge, since LangGraph's value is partly LangSmith. *Decision: no framework migration yet; revisit in Phase 5+.*

**Q2. Highest-leverage axis — speed or accuracy?**
*Answer:* Both are blockers but for different reasons. ~46 min makes the product **unusable**; weak extraction + un-verified figures make it **untrustworthy** — fatal for a credit tool. They are not either/or: the extraction upgrade (B2) improves accuracy *and* feeds the deterministic ratios, while parallelisation/structured-outputs (B1) fix speed. *Decision: run an "accuracy/trust" track and a "speed/cost" track in parallel, both gated by an eval harness.*

**Q3. Replace the deterministic ratio engine with an LLM extractor?**
*Answer:* No — **keep the deterministic ratio math** (it is the trust anchor that caught the AI's own error), but **upgrade what feeds it**. Use a single **structured-output LLM call** to extract line items into a **typed (Pydantic) schema with validation** (gross profit &#8776; revenue &#8722; COGS; assets = liabilities + equity) and a **source citation per figure**; then compute ratios in Python from the validated numbers. This is robust to messy PDFs/Excel/scans (fixing the exact live-test failure) while preserving arithmetic trust.

**Q4. How do we make quality measurable so the refactors are safe?**
*Answer:* Build an **eval harness**: ~10 golden businesses with expected key findings + known-correct ratios, plus an automated **grader** scoring (a) **faithfulness** — is every cited number traceable to source? and (b) **coverage** — were the planted issues caught? Run nightly or as a gated (paid) CI job. B1 names this the production differentiator. *Decision: the eval harness is a prerequisite, built first.*

**Q5. Add observability now?**
*Answer:* Yes — cheaply and early. Integrate **Langfuse** (open-source, async, OTEL) to trace every agent call with cost/latency/tokens. We would have *seen* the 46-minute breakdown and per-analysis cost. You cannot optimise what you cannot measure. *Decision: ship tracing as step 1 of the speed track.*

**Q6. What is Imara, commercially — lender, SME tool, or lender tool?**
*Answer:* **Not a lender** (do not compete with Lulalend). Imara is the **bankability / diagnostic + SA-compliance layer** sitting *before* and *beside* lenders, on a validated, enormous gap. Two wedges: **B2C** ("get bankable before you apply") and **B2B** (sell the Imara Score + compliance pre-screen as alternative data to funders who today use consumer-grade scoring). The **Imara Score is the productisable asset.** *Decision: make the Score + compliance outputs API-accessible, and add the SARS Statement-of-Account upload path for verified compliance — both serve the B2B wedge.*

**Q7. Reliability — in-memory state, single replica?**
*Answer:* A latent cliff (a restart loses in-flight analyses; no horizontal scale). Move status to the DB and add a real task queue **before** real traffic — medium priority, after speed/accuracy.

**Q8. Security/privacy — UUID-only access, no auth?**
*Answer:* For real client financials this is a **POPIA-relevant gap** (ironic, given Imara audits POPIA). Per-user auth + signed/expiring share links are required **before** onboarding any real business. High priority before real data.

---

## PART D — The improvement plan (prioritised & sequenced)

**Phase 0 — Foundations (measure before you change). ~1 focused session.**
- **Eval harness** — golden dataset + automated faithfulness/coverage grader; gated CI job.
- **Observability** — Langfuse (or OTEL) tracing of every agent call: cost, latency, tokens, per analysis.
- *Why first:* every later change (speed, prompts, extraction) needs a quality and cost yardstick.

**Phase 1 — Accuracy & trust.**
- **LLM structured extraction** into a validated typed schema (balance-sheet-balances check; source citations), feeding the existing deterministic ratio engine. Fixes the parser's real-world fragility.
- **Faithfulness verification** — reject/flag any AI-cited figure not traceable to the source documents.
- *Guarded by Phase 0.*

**Phase 2 — Speed & cost (target ~46 min &#8594; ~1&#8211;2 min).**
- **Parallelise** the independent Phase-2 agents (async fan-out).
- **Structured outputs** — one call per agent (delete the second "parse" call).
- **Prompt caching** on the shared context prefix; **model routing** (cheap model for extraction/parse, strong model for synthesis).
- *Guarded by Phase 0; ~70&#8211;85% time/cost reduction projected.*

**Phase 3 — Reliability & scale.**
- DB-backed (or Redis) analysis status + a proper task queue; per-analysis cost/usage records.

**Phase 4 — Security & product surface.**
- Per-user **authentication** + access-controlled, expiring report links.
- **API access** to the Imara Score + compliance outputs (B2B wedge); **SARS Statement-of-Account upload** for verified balances.

**Phase 5 — Calibration & strategy.**
- Back-test / calibrate the Imara Score weights against real outcomes (AHP / regression).
- Commit to a go-to-market wedge (B2C vs B2B-to-lenders) and shape the roadmap around it.
- Re-evaluate a **LangGraph** migration if stateful workflows + checkpoints now justify it.

**Sequencing rationale:** Phase 0 makes everything else safe and measurable; Phases 1&#8211;2 fix the two existential issues (trust, speed) the live test exposed; Phase 3 prevents a reliability cliff; Phase 4 is the gate before real client data and the B2B opportunity; Phase 5 turns a working tool into a calibrated, strategically-aimed product.

---

## Sources
- LangChain — AI agent frameworks 2026: https://www.langchain.com/resources/ai-agent-frameworks
- Multi-agent orchestration frameworks 2026 (Presenc): https://presenc.ai/research/multi-agent-orchestration-frameworks-2026
- Automated financial-statement extraction with LLMs (Cognica): https://www.cognica.io/en/blog/posts/2025-11-18-llm-pdf-financial-statement-extraction
- Financial-statement extraction (LlamaIndex): https://www.llamaindex.ai/services/ocr-for-financial-statements
- Langfuse — LLM observability: https://langfuse.com/docs/observability/overview
- LLM observability tools 2026 (Confident AI): https://www.confident-ai.com/knowledge-base/compare/top-7-llm-observability-tools
- SME funding landscape SA 2025: https://smesouthafrica.co.za/sme-funding-landscape-in-south-africa-highlights-from-the-2025-report/
- SA FinTech lending market (Ken Research): https://www.kenresearch.com/south-africa-fintech-lending-bnpl-market
- SME lending in Africa — alternative data (ezbob): https://ezbob.com/sme-lending-in-africa-alternative-data-drives-credit-decisions/
