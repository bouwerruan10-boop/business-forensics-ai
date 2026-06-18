# Business Forensics AI — Improvement Plan v2.0

**Prepared:** June 2026  
**Scope:** Four new AI agents · Three audience-specific PDF reports · Interactive HTML report · Enhanced action plan  
**Build order:** Backend data model → New agents → API endpoints → Report generators → Frontend

---

## Why This Plan Exists

Market research identified three compounding gaps in the current platform:

1. **Depth gap** — Competitors like Fathom and Spotlight Reporting generate summaries. We generate forensic findings. The next level is *prescriptive outputs*: what is this business worth, will a bank lend to it, and where are the fraud signals? These are the outputs that create urgency and justify premium pricing.

2. **Audience gap** — The same financial data means different things to an owner (fix it), a banker (is it safe?), and an investor (what can I make?). One PDF for all three is a missed opportunity. PE firms pay $50K for audience-targeted reports. We can generate three versions in seconds.

3. **Stickiness gap** — One-off PDF reports are consumed and forgotten. An interactive HTML report that lives in a browser tab — expandable, clickable, shareable — turns a one-time analysis into a working document clients return to.

---

## What We Are Building

| # | What | Where | Effort |
|---|------|--------|--------|
| 1 | Fraud & Anomaly Detection Agent | `specialist_agents.py` | Medium |
| 2 | Credit Readiness Agent | `specialist_agents.py` | Medium |
| 3 | Valuation Agent | `specialist_agents.py` | Medium |
| 4 | Forecast & Scenario Agent | `specialist_agents.py` | Medium |
| 5 | SharedMemory new fields | `shared_memory.py` | Small |
| 6 | CEO Agent scoring + report dict updates | `ceo_agent.py` | Medium |
| 7 | Audience-specific PDF (Owner/Banker/Investor) | `report_generator.py` | Large |
| 8 | Traffic light scorecard + credit/valuation sections | `report_generator.py` | Medium |
| 9 | Interactive HTML report generator | `html_report.py` (new) | Large |
| 10 | New API endpoints + audience query param | `main.py` | Small |
| 11 | Frontend: audience selector + new score cards | React components | Medium |

---

## Phase 1 — Data Model (Build First)

### File: `backend/memory/shared_memory.py`

**Add to `AgentFinding` dataclass** — no changes needed, all new agent data uses existing fields.

**Add to `SharedMemory` dataclass** (after `primary_concern` field, line ~55):

```python
# Fraud & Anomaly Detection
fraud_risk_level: str = "unknown"          # "low" | "medium" | "high" | "critical"
fraud_risk_score: int = 0                  # 0–100 (100 = highest risk)
fraud_indicators: list = field(default_factory=list)  # list of specific flags

# Credit Readiness
credit_score: int = 0                      # 0–100 credit readiness score
credit_grade: str = ""                     # "A" | "B" | "C" | "D" | "F"
credit_barriers: list = field(default_factory=list)   # what is blocking credit access
credit_strengths: list = field(default_factory=list)  # what supports credit application

# Valuation
valuation_low: float = 0.0                 # conservative valuation
valuation_mid: float = 0.0                 # base case valuation
valuation_high: float = 0.0               # optimistic valuation
valuation_method: str = ""                 # "DCF + Multiples" etc.
valuation_ebitda_multiple: float = 0.0

# Forecast
forecast_base_12m: float = 0.0            # base case 12-month revenue projection
forecast_bull_12m: float = 0.0            # bull case
forecast_bear_12m: float = 0.0            # bear case
forecast_assumptions: list = field(default_factory=list)
```

---

## Phase 2 — Four New Agents

### File: `backend/agents/specialist_agents.py`

Add all four classes before the `ALL_AGENTS` list at the bottom (currently line 516). Then add them to the list.

---

### Agent 12: Fraud & Anomaly Detection Agent

**Purpose:** Statistical fraud detection — goes beyond the existing AuditorAgent's control-weakness focus to specifically apply Benford's Law, digit pattern analysis, temporal anomalies, and cross-field inconsistencies. This is the agent a bank or PE firm uses before lending or acquiring.

**System prompt focus:**
- Benford's Law digit distribution on all numeric columns (flag deviations >15%)
- Round-number concentration (% of transactions ending in 000 or 00)
- Temporal clustering (unusual concentration of transactions on specific dates/times)
- Velocity anomalies (month where a metric moved >3 standard deviations from mean)
- Cross-field consistency (revenue growing while staff/costs flat = suspicious)
- Duplicate detection (same amount on same date from same category)
- Gap analysis (sequential numbering with gaps = possible deleted transactions)
- Revenue-to-cash reconciliation (revenue recorded but cash not received = timing manipulation)

**Output fields used:** All standard `AgentFinding` fields. Agent name: `"Fraud & Anomaly Detection Agent"`

**CEO scoring bucket:** `risk_agents` set (joins AuditorAgent, LegalRiskAgent)

**New SharedMemory update logic** (in this agent's `analyze()` method):
After parsing findings, calculate `fraud_risk_score` from count and severity of findings and write back to memory.

---

### Agent 13: Credit Readiness Agent

**Purpose:** Scores the business specifically for South African credit applications. Outputs a credit grade (A–F) and specific barriers. This directly addresses the 95% of SA SMEs excluded from credit.

**System prompt focus:**
- Debt service coverage ratio (DSCR = EBITDA / annual debt repayments; benchmark ≥1.25×)
- Current ratio (current assets / current liabilities; bank minimum typically 1.5×)
- Quick ratio (liquid assets only; benchmark ≥1.0×)
- Net profit margin trend (3+ consecutive months of positive = strong; losses = barrier)
- Revenue stability (coefficient of variation <20% = stable; >40% = high risk)
- Cash flow consistency (months with negative cash balance = red flag for lenders)
- Days Sales Outstanding (DSO) — high DSO = liquidity risk
- Leverage ratio (total debt / equity; banks prefer <2.0×)
- What specific SA funding products this business qualifies for (SEFA, IDC, NEF, ABSA Business, FNB Business, bank term loan, invoice financing, asset finance)
- What to fix to move up one credit grade

**Credit grade scale:**
- A (80–100): Bankable immediately. Multiple lenders will compete.
- B (60–79): Bankable with conditions. Address 1-2 specific issues.
- C (40–59): Needs 3-6 months improvement before approaching lenders.
- D (20–39): Significant restructuring required. Equity or grant funding more appropriate.
- F (0–19): Distressed. Turnaround required before any financing discussion.

**Output fields used:** Standard findings + write `credit_score`, `credit_grade`, `credit_barriers`, `credit_strengths` to SharedMemory.

**CEO scoring bucket:** New bucket `credit_agents` — contributes to `risk_score`.

---

### Agent 14: Valuation Agent

**Purpose:** Calculates what the business is worth using three methods. Essential for business brokers, PE, succession planning, divorce settlements, partner buyouts, and investor pitches.

**System prompt focus:**

**Method 1 — Earnings Multiple (primary)**
- Calculate normalised EBITDA (remove owner's salary above market, one-off costs, non-recurring income)
- Apply industry-appropriate SA EBITDA multiple:
  - Retail: 3–5×
  - Manufacturing: 4–6×
  - Services / professional: 4–7×
  - Technology / SaaS: 8–15×
  - Logistics: 3–5×
  - Healthcare: 6–10×
  - Food & beverage: 3–5×
- Discount for: customer concentration >30%, owner-dependent revenue, no management team, single-location
- Premium for: recurring revenue contracts, strong brand, IP, diversified customers

**Method 2 — DCF (for businesses with 3+ years data)**
- Project free cash flows at revenue growth rate inferred from data
- Apply WACC of 18–22% for SA SME (reflecting risk premium)
- Terminal value at 3× exit multiple

**Method 3 — Asset-Based (floor)**
- Total tangible assets minus liabilities
- Used as floor valuation — most relevant for asset-heavy businesses

**Output:** Three-point valuation range (low / mid / high) in business currency. Methodology disclosed. Write to `valuation_low`, `valuation_mid`, `valuation_high`, `valuation_method`, `valuation_ebitda_multiple` on SharedMemory.

---

### Agent 15: Forecast & Scenario Agent

**Purpose:** Forward-looking 12-month projection with three scenarios. Converts the platform from backward-looking forensics to a complete decision-support tool.

**System prompt focus:**

**Base Case Projection (most likely)**
- Extrapolate revenue trend from last 12 months (linear regression or CAGR)
- Apply identified cost improvements from other agents
- Project month-by-month for 12 months

**Bull Case (optimistic)**
- Revenue at +15% above trend (if all quick wins implemented)
- Cost ratios improve to industry median
- Working capital cycle tightened by 15 days

**Bear Case (conservative)**
- Revenue at -10% below trend (demand softness, competitor pressure)
- Costs remain sticky (no improvements)
- Cash impact modelled

**Key assumptions to state explicitly:**
- Revenue growth rate assumed
- Operating leverage assumed
- Working capital assumptions
- One-off items excluded

**Output:** Write `forecast_base_12m`, `forecast_bull_12m`, `forecast_bear_12m`, `forecast_assumptions` to SharedMemory. Return findings as standard `AgentFinding` objects describing each scenario.

---

### Updated `ALL_AGENTS` list

```python
ALL_AGENTS = [
    FinancialAgent,
    AccountingAgent,
    AuditorAgent,
    OperationsAgent,
    LogisticsAgent,
    SalesAgent,
    MarketingAgent,
    HRAgent,
    ProcurementAgent,
    StrategyAgent,
    LegalRiskAgent,
    FraudDetectionAgent,    # NEW
    CreditReadinessAgent,   # NEW
    ValuationAgent,         # NEW
    ForecastAgent,          # NEW
]
```

---

## Phase 3 — CEO Agent Updates

### File: `backend/agents/ceo_agent.py`

**Update `_score_business()` method:**
Add new scoring bucket for `credit_agents`:
```python
credit_agents = {"Credit Readiness Agent"}
credit_findings = [f for f in findings if f.agent in credit_agents]
credit_penalty = sum(_sev_weight(f) for f in credit_findings)
memory.credit_score = min(100, max(10, 100 - credit_penalty))
# Also write credit_grade to memory based on score
```

**Update `_generate_report()` method:**
Add new keys to the returned dict:
```python
# New agent outputs
"fraud_risk_level": memory.fraud_risk_level,
"fraud_risk_score": memory.fraud_risk_score,
"fraud_indicators": memory.fraud_indicators,
"credit_score": memory.credit_score,
"credit_grade": memory.credit_grade,
"credit_barriers": memory.credit_barriers,
"credit_strengths": memory.credit_strengths,
"valuation_low": memory.valuation_low,
"valuation_mid": memory.valuation_mid,
"valuation_high": memory.valuation_high,
"valuation_method": memory.valuation_method,
"valuation_ebitda_multiple": memory.valuation_ebitda_multiple,
"forecast_base_12m": memory.forecast_base_12m,
"forecast_bull_12m": memory.forecast_bull_12m,
"forecast_bear_12m": memory.forecast_bear_12m,
"forecast_assumptions": memory.forecast_assumptions,
```

**Update `_cross_agent_synthesis()` prompt:**
Add instruction for CEO to specifically reference credit readiness and valuation in the resolution paragraph.

**Update `_generate_executive_summary()` prompt:**
Add instruction: if credit_score < 60, paragraph 4 must address what to fix before approaching lenders.

---

## Phase 4 — Audience-Specific PDF Reports

### File: `backend/services/report_generator.py`

**Change `generate_pdf_report()` signature:**
```python
def generate_pdf_report(report: dict, audience: str = "owner") -> bytes:
```

**Three cover page variants:**

`_cover_page_owner(story, report)`:
- Headline: "Business Health Report"
- Sub: "Your Action Plan"
- Score displayed as a dial: 0–100 with colour
- Tagline: "Plain-language findings and a 30-day action plan for [Business Name]"

`_cover_page_banker(story, report)`:
- Headline: "Credit Assessment Report"
- Sub: "Financial Risk Analysis — For Lender Use"
- Credit grade displayed prominently (A/B/C/D/F with colour)
- DSCR, current ratio, quick ratio in cover summary table
- Tagline: "Prepared for lender review of [Business Name]"

`_cover_page_investor(story, report)`:
- Headline: "Investment Analysis Report"  
- Sub: "Value Creation Assessment"
- Valuation range displayed: "R X,XXX,XXX — R X,XXX,XXX"
- IRR potential highlighted
- Tagline: "Prepared for investor review of [Business Name]"

**New section: Traffic Light Scorecard (all audiences)**
```
_traffic_light_section(story, report):
```
A 3×4 grid of metric cards, each with:
- Metric name
- Current value
- Benchmark
- RAG status (Red/Amber/Green dot)

Metrics to show:
- Gross Margin vs benchmark
- Net Margin vs benchmark  
- Current Ratio vs 1.5 minimum
- Debtor Days vs 35-day benchmark
- Cash Trend (positive/negative 3-month)
- Revenue Growth (positive/flat/declining)
- Credit Grade (A through F)
- Fraud Risk (Low/Medium/High)
- Business Health Score (/100)
- Valuation Range
- EBITDA Multiple
- 12-Month Revenue Forecast

**New section: Credit Readiness (Banker + Owner reports)**
```
_credit_readiness_section(story, report):
```
- Credit score as a gauge (0–100)
- Grade displayed (A–F) with colour
- Two columns: Strengths (green) | Barriers (red)
- Which SA funding products the business qualifies for
- 3 specific actions to improve credit grade

**New section: Valuation Summary (Investor + Owner reports)**
```
_valuation_section(story, report):
```
- Three-point bar: Low | Mid | High in business currency
- Methodology disclosed (EBITDA multiple used, DCF rate)
- What drives the discount from mid to low
- What drives the premium from mid to high
- Sensitivity: "If EBITDA improves 20%, valuation increases to R X"

**New section: Fraud Risk Indicator (Banker + Investor reports)**
```
_fraud_risk_section(story, report):
```
- Fraud risk score (0–100) with gauge
- Top 3 anomaly flags with explanation
- Assessment: Clean / Requires Investigation / Material Risk
- Recommended action

**Audience-specific findings filter:**
- Owner report: all findings, sorted by quick_win first
- Banker report: financial, risk, accounting, fraud findings only
- Investor report: financial, strategy, valuation, forecast, sales findings only

---

## Phase 5 — Interactive HTML Report

### New file: `backend/services/html_report.py`

**Function signature:**
```python
def generate_html_report(report: dict) -> str:
    """Generate a self-contained HTML report. No external dependencies."""
```

**Structure (single-file, inline CSS + vanilla JS):**

```
<html>
  <head>
    Inline CSS: brand colours (navy/gold), responsive grid, card styles
    Inline SVG charts (score gauges, traffic lights)
  </head>
  <body>
    Section 1: Cover (business name, date, health score dial)
    Section 2: Traffic Light Scorecard (3×4 metric grid)
    Section 3: Executive Summary (4 paragraphs, collapsible)
    Section 4: Situation / Complication / Resolution
    Section 5: Priority Issues (expandable cards, click to expand detail)
    Section 6: Agent Findings (tabbed by agent, expandable per finding)
    Section 7: Quick Wins (30-day checklist with checkboxes)
    Section 8: 90-Day Roadmap (timeline layout)
    Section 9: Credit Readiness (score gauge + breakdown)
    Section 10: Valuation (three-point bar chart)
    Section 11: Forecast (3-line scenario chart, SVG)
    Section 12: Fraud Risk Indicator
    Footer: Generated by Business Forensics AI
  </body>
</html>
```

**Key interactivity (vanilla JS, no framework):**
- Click finding card → expand to show full detail, recommendation, ROI
- Tab navigation for agent sections
- Quick win checklist (check items off, localStorage persists)
- Print-friendly CSS (`@media print`) for clean printing

**SVG charts (generated inline, no matplotlib):**
- Score gauge: SVG arc chart (0–100)
- Traffic light grid: SVG coloured circles
- Valuation range: SVG bar with three points
- Forecast: SVG line chart (three scenario lines, month labels)

---

## Phase 6 — New API Endpoints

### File: `backend/main.py`

**Update PDF endpoint:**
```python
@app.get("/api/report/{analysis_id}/pdf")
def get_pdf(analysis_id: str, audience: str = "owner"):
    # audience: "owner" | "banker" | "investor"
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    pdf_bytes = generate_pdf_report(result, audience=audience)
    biz_name = result.get("business_name", "report").replace(" ", "_")
    filename = f"{biz_name}_{audience}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**New HTML report endpoint:**
```python
@app.get("/api/report/{analysis_id}/html")
def get_html_report(analysis_id: str):
    from services.html_report import generate_html_report
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    html = generate_html_report(result)
    biz_name = result.get("business_name", "report").replace(" ", "_")
    return Response(
        content=html.encode("utf-8"),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{biz_name}_interactive_report.html"'},
    )
```

**New credit report endpoint:**
```python
@app.get("/api/report/{analysis_id}/credit")
def get_credit_report(analysis_id: str):
    result = analyses.get(analysis_id) or get_report(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "business_name": result.get("business_name"),
        "credit_score": result.get("credit_score", 0),
        "credit_grade": result.get("credit_grade", "N/A"),
        "credit_barriers": result.get("credit_barriers", []),
        "credit_strengths": result.get("credit_strengths", []),
        "valuation_low": result.get("valuation_low", 0),
        "valuation_mid": result.get("valuation_mid", 0),
        "valuation_high": result.get("valuation_high", 0),
        "fraud_risk_level": result.get("fraud_risk_level", "unknown"),
        "fraud_risk_score": result.get("fraud_risk_score", 0),
    }
```

---

## Phase 7 — Frontend Updates

### File: `frontend/src/components/ReportActions.jsx`

**Add audience selector before PDF download:**
```jsx
const [audience, setAudience] = useState("owner")

// Audience picker UI — three toggle buttons:
// [Owner Report] [Banker Report] [Investor Report]

// PDF download now uses:
const pdfUrl = `/api/report/${analysisId}/pdf?audience=${audience}`

// New HTML report button:
const htmlUrl = `/api/report/${analysisId}/html`
```

### File: `frontend/src/components/ScoreCards.jsx`

**Add three new score cards after existing four:**
- Credit Score card: shows 0–100 score + grade letter (A–F) with colour
- Valuation card: shows "R X.XM — R X.XM" range (mid value prominent, low/high smaller)
- Fraud Risk card: shows "LOW / MEDIUM / HIGH / CRITICAL" with colour indicator

### New file: `frontend/src/components/CreditReport.jsx`

Full credit readiness panel displayed on Dashboard below ScoreCards:
- Score gauge (CSS circle)
- Grade badge
- Two-column layout: Strengths (green) | Barriers (red)
- Funding products available
- "How to move up a grade" — 3 specific actions

### New file: `frontend/src/components/ValuationPanel.jsx`

Valuation display panel:
- Three-point bar (Low / Mid / High)
- Methodology disclosed
- Sensitivity statement

### File: `frontend/src/components/Dashboard.jsx`

Add `<CreditReport />` and `<ValuationPanel />` components after `<ScoreCards />`.

---

## Build Order (sequential dependencies)

```
Step 1:  shared_memory.py        — add new fields
Step 2:  specialist_agents.py    — add 4 new agent classes
Step 3:  ceo_agent.py            — update scoring + report dict
Step 4:  report_generator.py     — audience param + new sections
Step 5:  html_report.py          — new service (self-contained)
Step 6:  main.py                 — new endpoints + audience param
Step 7:  ReportActions.jsx       — audience selector + HTML button
Step 8:  ScoreCards.jsx          — 3 new cards
Step 9:  CreditReport.jsx        — new component
Step 10: ValuationPanel.jsx      — new component
Step 11: Dashboard.jsx           — wire new components in
```

---

## Requirements Updates

### `backend/requirements.txt` — no new packages needed
All new agents use the existing anthropic client.  
HTML report uses only standard library + string formatting (no new dependencies).  
SVG charts are generated as inline strings (no matplotlib needed for HTML report).

---

## Success Criteria

When complete, the platform must:
1. Run 15 agents instead of 11 without breaking existing pipeline
2. Return `credit_score`, `credit_grade`, `valuation_mid`, `fraud_risk_level` in every report JSON
3. Generate three distinct PDF files from one analysis (Owner, Banker, Investor)
4. Generate a self-contained HTML file that works offline
5. Frontend shows credit score, valuation range, and fraud risk in score cards
6. All new endpoints return 200 on a completed analysis
7. Existing test data (Acme Retail SA) runs through the full pipeline successfully

---

## Estimated Token Cost Per Analysis (after expansion)

| Phase | API Calls | Est. tokens |
|-------|-----------|-------------|
| 11 existing agents (2 calls each) | 22 | ~88K |
| 4 new agents (2 calls each) | 8 | ~32K |
| CEO synthesis + report | 4 | ~24K |
| **Total per analysis** | **34** | **~144K** |

At claude-sonnet-4-6 pricing (~$3/MTok input, $15/MTok output), one full analysis costs approximately **$0.60–$1.20** depending on data size.

---

*End of Plan v2.0 — Ready to build.*
