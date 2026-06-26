# Imara — Intake Redesign & SA Specialist Agents
## Implementation Plan — June 2026

---

## Overview

The current two-page flow (7-field profile form → generic file drop zone) does not capture enough context to fully activate the SA-specific intelligence in the pipeline. This plan merges and extends that flow into a single smart intake experience with dedicated document zones and two new South Africa–specific specialist agents.

**Scope:** 8 tasks across frontend, backend agents, shared memory, and deployment.

---

## Part 1 — Redesigned Intake Form

### What changes

The current `BusinessProfile.jsx` + `FileUpload.jsx` two-step flow is replaced by a single `SmartIntake.jsx` with four collapsible sections. The user sees one page, fills it progressively, and submits everything at once.

### New profile fields

| Field | Purpose | Agent(s) that use it |
|---|---|---|
| Entity type (Pty/CC/Sole Prop/Trust/NPO) | Determines applicable company law & tax regime | SALegalAgent, SATaxAgent |
| CIPC registration number | Market research + legal compliance cross-check | MarketResearchAgent, SALegalAgent |
| VAT registered + VAT number | VAT201 compliance, input/output tax ratio | SATaxAgent |
| Tax year-end month | Aligns period analysis to correct year-end | FinancialAgent, SATaxAgent |
| Years in business | Gates business plan zone; calibrates benchmarks | StrategyAgent, ValuationAgent |
| BBBEE level (1–8 / Exempt / Non-compliant / Not verified) | Procurement advantage, BEE penalties, scorecard | SALegalAgent, StrategyAgent |
| Primary banking institution | Aligns credit readiness findings to lender criteria | CreditAgent |
| Report audience (Owner / Bank / Investor) | Tones CEO synthesis and report emphasis | CEOAgent |

### 6 dedicated document upload zones

Each zone tags uploaded files with a category label sent to the backend. The backend routes by category, not just file extension.

| Zone | Label sent | Required? | Routes to |
|---|---|---|---|
| Financial Records | `financial` | Yes | FinancialAgent, AccountingAgent, AuditorAgent |
| Bank Statements | `bank` | Yes | FinancialAgent, FraudAgent, CreditAgent |
| Tax Documents | `tax` | Optional | **SATaxAgent** |
| Legal Documents | `legal` | Optional | **SALegalAgent** |
| HR & Payroll | `hr` | Optional | HRAgent |
| Business Plan | `business_plan` | Optional (shown prominently for <3 yr businesses) | StrategyAgent, ValuationAgent |

### File acceptance

- Financial: Excel, CSV, PDF
- Bank: PDF, CSV, Excel
- Tax: PDF, Excel
- Legal: PDF (Word .docx support via text extraction)
- HR: Excel, PDF, CSV
- Business Plan: PDF, Word

---

## Part 2 — Two New SA Specialist Agents

### Current gap

`LegalRiskAgent` exists but is generic commercial law. It mentions BBBEE and POPIA in passing but does not apply specific SA statutes, tax forms, or CIPC-specific compliance. There is no dedicated tax agent at all — tax risk is spread thinly across `AuditorAgent` and `LegalRiskAgent`.

### 2a — SATaxAgent

**File:** `backend/agents/specialist_agents.py` (new class, appended)

**Activation:** Always runs when tax documents are uploaded (`tax` category). Falls back to running on financials + profile data if no tax docs present.

**Prompt focus areas:**

1. **VAT compliance** — Act 89 of 1991. Input/output tax ratio analysis. Late submission pattern from VAT201 data. Zero-rated vs exempt classification errors.
2. **Corporate income tax** — Income Tax Act 58 of 1962. IT14 return completeness. Deductible vs non-deductible spend. Section 12E small business rate qualification.
3. **PAYE & SDL** — EMP201 accuracy. IRP5 vs payroll reconciliation. Employment Tax Incentive (ETI) eligibility.
4. **Provisional tax** — IRP6 completeness. Underestimation penalty risk (>80% rule).
5. **Tax clearance** — Certificate status. Good standing for government/tender work.
6. **SARS debt** — Outstanding returns, payment arrangements, interest accrual.

**Output fields added to SharedMemory:**
- `sa_tax_risk_score` (0–100)
- `sa_tax_findings` (list of Finding objects with severity)
- `sa_tax_summary` (text for CEO synthesis)
- `sa_vat_status` (compliant / risk / unknown)
- `sa_tax_clearance_status` (valid / expired / not provided / unknown)

### 2b — SALegalAgent

**File:** `backend/agents/specialist_agents.py` (new class, appended)

**Activation:** Always runs when legal documents are uploaded. Also runs on profile data alone (entity type, CIPC number, BBBEE level) even without docs.

**Prompt focus areas:**

1. **Companies Act 71 of 2008** — MOI compliance, annual return lodgement (CoR30.1), director duties (section 76), prescribed officer obligations, annual financial statement filing thresholds.
2. **BBBEE Act 53 of 2003** (+ Broad-Based BEE Codes of Good Practice) — Scorecard element analysis (ownership, management, skills, ESD, socio-economic). Front-loading and misrepresentation risk.
3. **POPIA (Act 4 of 2013)** — Data subject rights, lawful processing basis, Information Officer appointment, breach notification obligations, cross-border transfer restrictions.
4. **Labour Relations Act 66 of 1995** — Disciplinary procedure compliance, retrenchment obligations (section 189), bargaining council applicability.
5. **Consumer Protection Act 68 of 2008** — Returns policy compliance, implied warranty obligations, prohibited conduct (section 40–41), supply of services obligations.
6. **National Credit Act 34 of 2005** — If business extends credit: registration as credit provider, affordability assessments, prescribed rate of interest.
7. **CIPC compliance** — Annual return status, director changes, registered address accuracy, beneficial ownership register (BOE) filing.

**Output fields added to SharedMemory:**
- `sa_legal_risk_score` (0–100)
- `sa_legal_findings` (list of Finding objects)
- `sa_legal_summary` (text for CEO synthesis)
- `sa_bbbee_analysis` (structured: level, score elements, risk flags)
- `sa_cipc_status` (compliant / overdue / unknown)

---

## Part 3 — Document Routing Architecture

### Backend changes

**`backend/main.py`** — extend `/analyze` endpoint:

```python
# Current
async def analyze(files: list[UploadFile], profile: str = Form(...)):

# New
async def analyze(
    files: list[UploadFile],
    file_categories: str = Form("[]"),   # JSON array: ["financial","bank","tax",...]
    profile: str = Form(...),
):
    categories = json.loads(file_categories)
    file_map = {files[i]: categories[i] if i < len(categories) else "general"
                for i in range(len(files))}
```

**`backend/services/file_parser.py`** — add category-aware parsing:

```python
def parse_files_by_category(file_map: dict) -> dict:
    """Returns {"financial": [...], "tax": [...], "legal": [...], ...}"""
```

**`backend/memory/shared_memory.py`** — add category buckets:

```python
uploaded_financial_text: str = ""
uploaded_bank_text: str = ""
uploaded_tax_text: str = ""
uploaded_legal_text: str = ""
uploaded_hr_text: str = ""
uploaded_plan_text: str = ""
```

Each specialist agent reads from its own bucket instead of the generic `uploaded_files_text` field.

### Frontend changes

**`frontend/src/components/SmartIntake.jsx`** — when building the FormData:

```javascript
const formData = new FormData()
fileBuckets.forEach((bucket, category) => {
  bucket.forEach(file => {
    formData.append('files', file)
    formData.append('file_categories', category)
  })
})
formData.append('profile', JSON.stringify(profileData))
```

---

## Part 4 — BBBEE Enhancement

The existing `StrategyAgent` prompt mentions BBBEE in passing. With the new `SALegalAgent` doing deep BBBEE analysis, the following additions tie everything together:

1. `SALegalAgent` produces `sa_bbbee_analysis` with element scores and risk flags.
2. `CEOAgent` synthesis prompt receives `sa_bbbee_analysis` and calls out procurement impact explicitly.
3. Dashboard gets a **BBBEE Scorecard** section in the SA compliance panel (new component: `SACompliancePanel.jsx`).
4. A BBBEE Score card is conditionally shown in `ScoreCards.jsx` alongside the Market Visibility card.

---

## Part 5 — Phased Build Order

### Phase 1 — Foundation (do first, everything else depends on it)

1. **Update `shared_memory.py`** — add all new intake fields + SA agent fields + doc category text buckets. Run import test.
2. **Update `main.py`** — accept `file_categories`, build file map, populate category text buckets in SharedMemory.

### Phase 2 — New agents

3. **Write `SATaxAgent`** — append to `specialist_agents.py`. Test standalone with mock SharedMemory.
4. **Write `SALegalAgent`** — append to `specialist_agents.py`. Test standalone.

### Phase 3 — Wire into pipeline

5. **Update `ceo_agent.py`** — add SATaxAgent and SALegalAgent to phase 1 (parallel with other specialists). Add their summaries to CEO synthesis context. Export new report fields.

### Phase 4 — Frontend

6. **Build `SmartIntake.jsx`** — four-section form with 6 upload zones. Map file_categories into FormData. Replace `BusinessProfile.jsx` + `FileUpload.jsx` in `App.jsx`.
7. **Build `SACompliancePanel.jsx`** — BBBEE scorecard + CIPC status + tax clearance status rendered in Dashboard.
8. Update `ScoreCards.jsx` — add BBBEE score card (conditional on `sa_legal_findings` present).

### Phase 5 — Deploy

9. Update `push_imara.bat` with new files.
10. Run bat, confirm Railway redeploy, smoke-test with demo data.

---

## Files to create / modify

| File | Action |
|---|---|
| `backend/memory/shared_memory.py` | Modify — add ~25 new fields |
| `backend/main.py` | Modify — file_categories param, doc routing |
| `backend/agents/specialist_agents.py` | Modify — append SATaxAgent + SALegalAgent classes |
| `backend/agents/ceo_agent.py` | Modify — wire 2 new agents, expand report dict |
| `backend/services/file_parser.py` | Modify — add category-aware parse function |
| `frontend/src/components/SmartIntake.jsx` | Create (new) |
| `frontend/src/components/SACompliancePanel.jsx` | Create (new) |
| `frontend/src/components/ScoreCards.jsx` | Modify — BBBEE card |
| `frontend/src/components/Dashboard.jsx` | Modify — add SACompliancePanel |
| `frontend/src/App.jsx` | Modify — replace profile/upload phases with SmartIntake |
| `push_imara.bat` | Modify — add new files to git add |

---

## Estimated complexity

| Task | Effort |
|---|---|
| SharedMemory fields | Low — dataclass fields only |
| main.py routing | Low — ~30 lines |
| SATaxAgent | Medium — prompt engineering + field mapping |
| SALegalAgent | Medium — prompt engineering + field mapping |
| ceo_agent.py wiring | Low — follow existing pattern |
| SmartIntake.jsx | High — largest frontend component in the app |
| SACompliancePanel.jsx | Medium — new dashboard panel |
| ScoreCards.jsx | Low — one new conditional card |
| Dashboard.jsx | Low — add one panel import |
| App.jsx | Low — change phase routing |

Total: ~2–3 hours of implementation.

---

*Ready to implement. Start with Phase 1 (SharedMemory + main.py) on your say-so.*
