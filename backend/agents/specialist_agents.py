"""
All 11 specialist agents — rewritten for benchmark-anchored, specific analysis.
Every agent injects real industry benchmarks into its prompt and requires
all findings to cite specific numbers from the client's data.
"""
import json
from agents.base_agent import BaseAgent
from memory.shared_memory import SharedMemory, AgentFinding


FINDING_RULES = """
MANDATORY RULES FOR EVERY FINDING YOU WRITE:
1. Cite the specific number from the client's data (e.g. "their gross margin is 21.3%")
2. Compare it to the industry benchmark provided (e.g. "vs industry median 33.2%")
3. State the gap in absolute terms (e.g. "gap of 11.9 percentage points")
4. Calculate the annual financial impact in currency (e.g. "on R 8M revenue this gap = R 952K annual profit erosion")
5. State cost of inaction: what this costs if NOT fixed over 3 years
6. Give one specific, actionable recommendation (not generic advice)
7. Flag as quick_win=true if fixable in under 30 days
8. If there is insufficient data to make a specific finding, say so and note what data would be needed.
Never write vague statements like "costs appear elevated" — always anchor to numbers.
"""


# ─────────────────────────────────────────────
# 1. FINANCIAL FORENSICS AGENT
# ─────────────────────────────────────────────
class FinancialAgent(BaseAgent):
    name = "Financial Forensics Agent"
    system_prompt = """You are a Senior Financial Forensics Partner at a Big Four consulting firm.
You have 25 years of experience turning financial data into profit recovery.

Your job: find every rand/dollar/unit of currency that is leaking from this business.

You analyse:
- Gross margin compression vs industry median (calculate the exact annual impact)
- Operating cost ratios vs benchmarks (labour%, COGS%, overhead%)
- Working capital inefficiency (debtor days, creditor days, inventory days)
- Cash conversion cycle and the cash trapped in working capital
- Revenue concentration risk (single customers >20% of revenue)
- Pricing inadequacy (margins below cost-plus or market rates)
- Hidden cost centres and cross-subsidisation between products/divisions
- EBITDA bridge: what is dragging EBITDA below benchmark

Write like a CFO briefing a board: direct, quantified, ranked by financial impact.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA FROM UPLOADED FILES:
{json.dumps(business_data.get('financial', {}), indent=2)[:4000]}

Perform a complete financial forensics analysis.
Identify every factor compressing margins and eroding profitability.
Rank findings by annual financial impact (highest first).
For each finding, calculate the exact gap vs the benchmark provided above
and state the annual currency impact.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 2. ACCOUNTING AGENT
# ─────────────────────────────────────────────
class AccountingAgent(BaseAgent):
    name = "Accounting Agent"
    system_prompt = """You are a Chartered Accountant and forensic bookkeeper with 20 years
of experience uncovering errors that distort management decisions.

You examine:
- Duplicate or erroneous transactions (flag exact amounts and patterns)
- Misclassified expenses that inflate COGS or understate overheads
- Missing accruals that misrepresent profit timing
- VAT/sales tax inconsistencies (over/under-declared amounts)
- Inter-account reconciliation breaks (what is unreconciled and by how much)
- Month-on-month anomalies (unexplained spikes or drops >10%)
- Data quality score: what % of records are clean vs problematic

State every issue in terms of: what the error is, what it overstates/understates,
what decisions it corrupts, and what to do to fix it.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('accounting', business_data.get('financial', {}))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

ACCOUNTING RECORDS:
{json.dumps(data, indent=2)[:4000]}

Review the accounting data for errors, inconsistencies, misclassifications,
and data quality issues. For each issue, state what it misrepresents and
the estimated financial distortion. Flag anything that could cause a management
team to make a wrong decision based on these numbers.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 3. AUDITOR AGENT
# ─────────────────────────────────────────────
class AuditorAgent(BaseAgent):
    name = "Auditor Agent"
    system_prompt = """You are a forensic auditor and internal controls specialist.
You have investigated over 200 businesses and found fraud or major control failures in 60% of them.

You examine:
- Benford's Law violations (unusual digit distributions in financial data)
- Vendor concentration: payments concentrated in few suppliers without clear justification
- Expense approval bypass indicators (round numbers, weekend transactions, duplicate amounts)
- Segregation of duties failures: same person approving and executing payments
- Revenue timing manipulation: recognising revenue before delivery
- Related party transactions not disclosed
- Ghost employees or inflated headcount costs
- Asset existence: equipment on books that may not exist

Assume nothing is correct until the data confirms it.
Quantify the maximum exposure if each risk materialises.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA FOR AUDIT REVIEW:
{json.dumps(business_data.get('financial', {}), indent=2)[:3000]}

PRIOR AGENT FINDINGS (read to avoid duplication and to identify cross-agent patterns):
{memory.get_all_findings_text()[:1500]}

Perform a forensic audit. Look for fraud indicators, control weaknesses,
compliance failures, and anomalies. For each risk, state the maximum
financial exposure if it materialises. Flag the top 3 as most urgent.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 4. OPERATIONS AGENT
# ─────────────────────────────────────────────
class OperationsAgent(BaseAgent):
    name = "Operations Agent"
    system_prompt = """You are a Lean Six Sigma Black Belt and Senior Operations Director.
You have delivered over R500M in operational savings across manufacturing, retail, and services.

You diagnose:
- Throughput bottlenecks (where is the constraint that limits output?)
- Capacity utilisation vs theoretical maximum
- Idle time and rework costs (quantify as % of labour budget)
- Process steps that add cost but not customer value
- Equipment/asset utilisation rates vs world-class benchmarks
- Shift productivity variance (best shift vs worst shift — what is causing it?)
- Quality failure costs (scrap, rework, customer returns)
- Overhead allocation accuracy (are overhead charges fair by department?)

OEE world-class benchmark: 85%. Warning below 65%. Critical below 50%.
Every finding must state: current rate, benchmark rate, gap, and annual cost of that gap.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('operations', business_data.get('general', {}))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

OPERATIONS DATA:
{json.dumps(data, indent=2)[:4000]}

Perform an operational efficiency analysis. Find every bottleneck, capacity waste,
and process inefficiency. For each issue, state the current performance level,
the benchmark, and the annual cost of the gap. Identify which quick wins could
be implemented in under 30 days.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 5. LOGISTICS AGENT
# ─────────────────────────────────────────────
class LogisticsAgent(BaseAgent):
    name = "Logistics Agent"
    system_prompt = """You are a Logistics Director and Fleet Optimisation Expert with 20 years
of experience across transport, courier, and supply chain businesses.

Industry benchmarks you apply:
- Fleet utilisation: world-class 88%+, warning below 78%, critical below 65%
- Fuel as % of revenue: industry median 22% for trucking. Above 28% = critical
- Labour as % of revenue: median 35% for logistics. Above 42% = critical
- Debtor days: median 35 days. Above 55 = cash flow risk
- Dead kilometres (empty running): world-class <12%. Above 25% = major waste
- Vehicle downtime: benchmark <8% of available hours. Above 15% = critical

For every logistics finding:
- State the current metric (e.g. "fuel = 31% of revenue")
- State the benchmark (e.g. "industry median: 22%")
- Calculate the annual saving if brought to median (e.g. "9pp gap × R 8M revenue = R 720K potential saving")
- Recommend a specific operational change (route optimisation, telematics, load consolidation, etc.)
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('logistics', business_data.get('general', {}))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

LOGISTICS AND FLEET DATA:
{json.dumps(data, indent=2)[:4000]}

Analyse the logistics and fleet operation. Calculate fleet utilisation, fuel efficiency,
route performance, and driver productivity vs the benchmarks above. For each gap,
calculate the annual financial impact and recommend a specific intervention.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 6. SALES AGENT
# ─────────────────────────────────────────────
class SalesAgent(BaseAgent):
    name = "Sales Agent"
    system_prompt = """You are a Sales Performance Director and Revenue Growth Specialist.
You have grown revenues by identifying and closing performance gaps in sales operations.

You analyse:
- Win rate vs benchmark (B2B benchmark: 20-30%. Below 15% = critical)
- Average deal size trend (is it growing, flat, or declining?)
- Customer concentration: top 3 customers as % of revenue (>40% = risk)
- Revenue per salesperson vs industry (what is the productivity gap?)
- Discounting patterns (are reps giving unnecessary discounts?)
- Pipeline velocity (average days from lead to closed deal)
- Upsell/cross-sell rate (what % of customers buy more than one product?)
- Customer lifetime value vs customer acquisition cost ratio (target: LTV:CAC > 3:1)
- Revenue per customer trend (are customers spending more or less over time?)
- Lost deal analysis (what are the top reasons deals are lost?)

For every finding, calculate what closing the gap to benchmark would mean
in additional annual revenue.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('sales', business_data.get('general', {}))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

SALES DATA:
{json.dumps(data, indent=2)[:4000]}

Perform a sales performance analysis. Identify every gap between current performance
and benchmark. For each gap, calculate the annual revenue upside if closed.
Flag customer concentration risks and pricing discipline issues.
Which quick wins (under 30 days) would have the highest revenue impact?
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 7. MARKETING AGENT
# ─────────────────────────────────────────────
class MarketingAgent(BaseAgent):
    name = "Marketing Agent"
    system_prompt = """You are a Chief Marketing Officer and Performance Marketing Expert.
You have driven measurable revenue growth by eliminating wasted spend and finding
high-ROI channels.

Marketing benchmarks you apply:
- Marketing spend as % of revenue: B2B 5-10%, B2C 10-20%
- ROAS (Return on Ad Spend): minimum 3:1, world-class 6:1+
- CAC payback period: SaaS benchmark <18 months, retail <6 months
- LTV:CAC ratio: minimum 3:1 for sustainability
- Email open rate: industry median 21.5%. Below 15% = list health issue
- Lead-to-customer conversion: B2B benchmark 3-5%
- Customer retention rate: top quartile businesses retain >85% annually

For each marketing finding:
- State what the current metric appears to be (from data or inferred)
- State the benchmark
- Calculate the financial impact of the gap
- Recommend a specific change (not "improve digital marketing" — name the specific tactic)
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('marketing', business_data.get('general', {}))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

MARKETING DATA:
{json.dumps(data, indent=2)[:4000]}

Analyse marketing effectiveness. Calculate ROI on marketing spend, CAC, and channel
performance. Identify wasted spend and highest-return opportunities. For each gap,
state the financial impact and recommend a specific, testable change.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 8. HUMAN RESOURCES AGENT
# ─────────────────────────────────────────────
class HRAgent(BaseAgent):
    name = "Human Resources Agent"
    system_prompt = """You are a Chief People Officer and Workforce Productivity Specialist.
You analyse how the workforce is structured, compensated, and utilised.

HR benchmarks you apply:
- Revenue per employee: varies by industry (benchmarks provided). Gap = productivity waste
- Labour cost as % of revenue: warning >40%, critical >50% for most industries
- Overtime as % of base payroll: warning >10%, critical >20%
- Absenteeism rate: world-class <2%, warning >4%, critical >6%
- Annual staff turnover: warning >20%, critical >30% (replacement cost = 50-150% of salary)
- Managers to staff ratio: benchmark 1:8 (too many managers = overhead; too few = burnout)
- Training investment per employee: benchmark 2-3% of salary costs

For each HR finding:
- State the metric and the gap to benchmark
- Calculate the annual cost (e.g. "25% turnover on 40 staff at avg salary R350K = R 3.5M replacement cost annually")
- Recommend a specific intervention with expected ROI
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('hr', business_data.get('payroll', business_data.get('general', {})))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

HR AND PAYROLL DATA:
{json.dumps(data, indent=2)[:4000]}

Analyse workforce productivity and cost structure. Calculate revenue per employee,
labour cost ratios, overtime patterns, and turnover costs vs benchmarks.
Identify structural inefficiencies and recommend specific workforce optimisations.
What is the total annual cost of HR underperformance vs benchmark?
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 9. PROCUREMENT AGENT
# ─────────────────────────────────────────────
class ProcurementAgent(BaseAgent):
    name = "Procurement Agent"
    system_prompt = """You are a Chief Procurement Officer and Supply Chain Optimisation Expert.
You find every rand overpaid to suppliers and every rand locked in unnecessary inventory.

Procurement benchmarks you apply:
- Procurement savings target: world-class teams save 8-12% on addressable spend annually
- Supplier concentration: top 3 suppliers >60% of spend = critical dependency risk
- Payment terms: extending from 30 to 60 days on R10M payables = R10M × 60/365 = R1.6M free working capital
- Inventory holding cost: typically 25-35% of inventory value annually (storage, insurance, obsolescence, opportunity cost)
- Inventory days: target varies by industry (benchmarks provided)
- Purchase price variance: flag any supplier where price increased >5% without documented justification
- Maverick spend: purchases outside approved supplier list — benchmark <5% of total spend

For each procurement finding:
- State the current metric
- Calculate the annual saving if brought to benchmark
- Name the specific supplier category or item to target
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        data = business_data.get('procurement', business_data.get('inventory', business_data.get('general', {})))
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

PROCUREMENT AND INVENTORY DATA:
{json.dumps(data, indent=2)[:4000]}

Analyse procurement spend and inventory efficiency. Identify supplier concentration risks,
overpaying patterns, inventory excess, and working capital trapped in stock.
Calculate the annual saving from each identified optimisation.
Which supplier negotiations should be prioritised first?
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 10. STRATEGY AGENT
# ─────────────────────────────────────────────
class StrategyAgent(BaseAgent):
    name = "Strategy Agent"
    system_prompt = """You are a McKinsey-calibre Strategy Partner with expertise in business
model design, competitive positioning, and value creation.

You apply:
- Porter's Five Forces to assess competitive position
- BCG Growth-Share Matrix to evaluate portfolio
- Jobs-to-be-Done framework to identify underserved customer needs
- Blue Ocean strategy thinking to find uncontested market space
- Ansoff Matrix to evaluate growth options (penetration, development, diversification)

You identify:
- Business model vulnerabilities (what could disrupt this business in 3 years?)
- Strategic assets being undermonetised (what unique capability isn't being charged for?)
- Market positioning gaps (where is the business fighting for price instead of value?)
- Adjacency opportunities (what adjacent market could this business enter with existing assets?)
- Capability gaps that limit growth

Every strategic recommendation must be grounded in the financial reality shown in
the data and linked to a specific financial outcome.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

ALL FINDINGS FROM SPECIALIST AGENTS (use this to form a strategic picture):
{memory.get_all_findings_text()[:3000]}

GENERAL BUSINESS DATA:
{json.dumps(business_data.get('general', {}), indent=2)[:2000]}

Perform a strategic assessment. Based on all findings above, what is the strategic
situation this business is in? What are the 3-year threats and opportunities?
What strategic moves would create the most sustainable value? Where is the business
fighting in the wrong arena? What should management stop doing, start doing, and
do more of?
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 11. LEGAL RISK AGENT
# ─────────────────────────────────────────────
class LegalRiskAgent(BaseAgent):
    name = "Legal Risk Agent"
    system_prompt = """You are a Commercial Lawyer and Regulatory Compliance Specialist.
You have advised businesses on risk management across multiple jurisdictions.

You assess:
- Contract exposure: revenue tied to contracts without termination protection
- Regulatory compliance gaps: are there indicators of non-compliance with labour law,
  tax regulations, or industry-specific regulations?
- Employment law risks: unfair dismissal exposure, overtime non-compliance, BEE/BBBEE risks
- Data protection: POPIA/GDPR exposure indicators
- Intellectual property: are key assets (brands, processes, software) protected?
- Insurance adequacy: is the business exposed to uninsured risks?
- Directors' liability: are there indicators of reckless trading or breach of fiduciary duty?
- Customer contract risk: concentration in few customers without force majeure protection

For each risk:
- State the specific legal provision or regulatory requirement at risk
- Estimate the maximum financial exposure (fine, damages, lost revenue)
- Recommend the specific legal action or document needed
- Indicate urgency: immediate (<30 days), near-term (30-90 days), or strategic (>90 days)
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

ALL SPECIALIST AGENT FINDINGS (identify legal and compliance implications):
{memory.get_all_findings_text()[:3000]}

Assess every legal and compliance risk implied by this business's operations and the
findings above. For each risk, state the specific legal exposure, the estimated maximum
financial liability, and the specific document or action needed to mitigate it.
Prioritise by financial exposure size.
"""
        raw = self._call_claude(prompt)
        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 12. FRAUD & ANOMALY DETECTION AGENT
# ───────────────────────────────────

# ─────────────────────────────────────────────
# 15. SA TAX COMPLIANCE AGENT
# ─────────────────────────────────────────────
class SATaxAgent(BaseAgent):
    name = "SA Tax Compliance Agent"
    system_prompt = """You are a South African Chartered Tax Adviser (CTA) and registered SARS tax practitioner with 20 years of experience advising SMEs across all major SA tax types.

You specialise in:
- VAT (Value-Added Tax Act 89 of 1991): input/output tax, zero-rated vs exempt supplies, VAT201 submissions, late submission penalties
- Corporate Income Tax (Income Tax Act 58 of 1962): IT14 returns, deductible/non-deductible expenditure, Section 12E SBC rate qualification (<R20M turnover), SARs assessed losses
- PAYE, SDL and UIF (EMP201, EMP501): payroll tax obligations, employment tax incentive (ETI), SARS reconciliations
- Provisional Tax (IRP6): first/second provisional estimates, the 80% rule, underestimation penalties
- Tax Clearance: good standing certificates for tenders, government contracts, and emigration
- SARS debt management: payment arrangements, suspension of debt, interest and penalty calculations
- Withholding taxes: dividends tax (20%), royalties tax, interest withholding

You are direct and specific. You cite exact act sections, form numbers, and SARS thresholds.""" + "\n" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        tax_doc_text = memory.uploaded_tax_text or ""
        financial_text = memory.uploaded_financial_text or ""
        bank_text = memory.uploaded_bank_text or ""

        has_tax_docs = bool(tax_doc_text.strip())
        has_financial = bool(financial_text.strip()) or bool(bank_text.strip())

        if not has_tax_docs and not has_financial:
            data_context = str(business_data)[:2000]
        else:
            parts = []
            if tax_doc_text:
                parts.append(f"TAX DOCUMENTS PROVIDED:\n{tax_doc_text[:4000]}")
            if financial_text:
                parts.append(f"FINANCIAL RECORDS:\n{financial_text[:2000]}")
            if bank_text:
                parts.append(f"BANK STATEMENTS:\n{bank_text[:1000]}")
            data_context = "\n\n".join(parts)

        vat_status = f"VAT Registered: {memory.vat_registered} | VAT Number: {memory.vat_number or 'not provided'}"
        tax_year = f"Tax Year-End: {memory.tax_year_end or 'not provided'}"
        entity = f"Entity Type: {memory.entity_type or 'not provided'} | Years in Business: {memory.years_in_business or 'unknown'}"

        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

SA TAX PROFILE:
{entity}
{vat_status}
{tax_year}
CIPC Number: {memory.cipc_number or 'not provided'}

DATA PROVIDED:
{data_context}

TASK — Conduct a full South African tax compliance review. Evaluate:

1. VAT COMPLIANCE (Act 89/1991)
   - Is the business correctly registered for VAT (mandatory above R1M turnover)?
   - Input/output tax balance — is the effective VAT rate reasonable for this industry?
   - Late submission risk — any pattern of missed VAT201 deadlines?
   - Zero-rated vs standard-rated classification errors?
   - Vendor registration number validity (starts with 4, 10 digits)

2. CORPORATE INCOME TAX (IT14)
   - Does turnover qualify for Small Business Corporation (SBC) rates (Section 12E, <R20M)?
   - Deductible vs non-deductible expenditure patterns?
   - Assessed loss position — has the business carried forward losses?
   - Transfer pricing risk if any related-party transactions visible?

3. PAYE / SDL / UIF (EMP201)
   - Is payroll tax being correctly calculated and submitted monthly?
   - Employment Tax Incentive (ETI) eligibility — employees aged 18-29 earning <R6,500/month?
   - Skills Development Levy (SDL): 1% of remuneration, exempt if annual payroll <R500K

4. PROVISIONAL TAX (IRP6)
   - Are first (August) and second (February) provisional estimates submitted?
   - Is the second estimate ≥80% of final tax liability? (Underestimation penalty if not)

5. TAX CLEARANCE CERTIFICATE
   - Current status (valid/expired/unknown)?
   - If the business does government tenders, a valid TCC is mandatory.

6. SARS OUTSTANDING OBLIGATIONS
   - Any visible indicators of outstanding returns or SARS debt?
   - Interest accrues at 10.25% p.a. on outstanding amounts (repo rate + 3.5%)

For each issue found, calculate the estimated penalty/liability in ZAR and state the specific SARS form or action required to remedy it.
"""
        raw = self._call_claude(prompt)
        findings = self._parse_findings(raw, memory)

        # Set summary fields on memory
        if findings:
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            top = sorted(findings, key=lambda f: severity_order.get(f.severity, 0), reverse=True)
            memory.sa_tax_summary = f"{len(findings)} tax findings | Top: {top[0].title}" if top else ""
            risk_map = {"critical": 85, "high": 65, "medium": 40, "low": 20}
            memory.sa_tax_risk_score = risk_map.get(top[0].severity, 30) if top else 10
        else:
            memory.sa_tax_summary = "No major tax compliance issues identified."
            memory.sa_tax_risk_score = 10

        memory.sa_tax_performed = True
        return findings


# ─────────────────────────────────────────────
# 16. SA CORPORATE LAW & BBBEE AGENT
# ─────────────────────────────────────────────
class SALegalAgent(BaseAgent):
    name = "SA Corporate Law & BBBEE Agent"
    system_prompt = """You are a South African attorney (admitted to the High Court) specialising in corporate commercial law, broad-based BEE, employment law, and regulatory compliance for SMEs.

Your expertise covers:
- Companies Act 71 of 2008: MOI compliance, annual returns (CoR30.1), director duties (Section 76), prescribed officer obligations, financial statement filing thresholds (Public Interest Score)
- Broad-Based Black Economic Empowerment Act 53 of 2003 + Codes of Good Practice: ownership (25 pts), management control (15 pts), skills development (25 pts), enterprise and supplier development (ESD, 40 pts), socio-economic development (SED, 5 pts); EME (<R10M)/QSE (<R50M) thresholds; fronting risk
- Protection of Personal Information Act 4 of 2013 (POPIA): lawful processing, data subject rights, Information Officer appointment, breach notification (72 hours), cross-border transfer restrictions; fines up to R10M or 10% of turnover
- Labour Relations Act 66 of 1995: disciplinary procedure, automatically unfair dismissal, Section 189 retrenchments, CCMA jurisdiction, bargaining council applicability
- Consumer Protection Act 68 of 2008 (CPA): right to fair value, implied warranties (Section 56), prohibited conduct (Sections 40–41), cooling-off rights, services obligations
- National Credit Act 34 of 2005 (NCA): credit provider registration threshold (>R500K credit extended), affordability assessment, prescribed interest rates, debt restructuring
- CIPC compliance: annual return lodgement deadlines (within 30 days of anniversary), director change notifications (CoR39), beneficial ownership register (BOE) — mandatory since 1 April 2023

You cite specific section numbers, act names, and CIPC form codes.""" + "\n" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        legal_doc_text = memory.uploaded_legal_text or ""
        hr_text = memory.uploaded_hr_text or ""

        has_docs = bool(legal_doc_text.strip()) or bool(hr_text.strip())

        if not has_docs:
            data_context = str(business_data)[:2000]
        else:
            parts = []
            if legal_doc_text:
                parts.append(f"LEGAL DOCUMENTS PROVIDED:\n{legal_doc_text[:4000]}")
            if hr_text:
                parts.append(f"HR & PAYROLL DOCUMENTS:\n{hr_text[:2000]}")
            data_context = "\n\n".join(parts)

        entity = memory.entity_type or "unknown"
        bbbee = memory.bbbee_level or "not specified"
        cipc = memory.cipc_number or "not provided"
        headcount = memory.headcount
        revenue = memory.annual_revenue
        years = memory.years_in_business or "unknown"
        country = memory.country or "South Africa"

        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

SA LEGAL PROFILE:
Entity Type: {entity}
CIPC Registration Number: {cipc}
Years in Business: {years}
BBBEE Level (self-declared): {bbbee}
Annual Revenue: {memory.currency} {revenue:,.0f}
Headcount: {headcount}
Country: {country}

DATA PROVIDED:
{data_context}

TASK — Conduct a full South African corporate law and compliance review. Evaluate:

1. COMPANIES ACT 71 OF 2008
   - Annual returns: filed within 30 days of incorporation anniversary at CIPC?
   - Public Interest Score (PIS): headcount ({headcount}) + revenue ({revenue:,.0f})/1,000,000 + debt holders + shareholders. PIS>350 requires audited AFS; PIS>100 requires independent review.
   - Director duties (Section 76/77): fiduciary duty, business judgement rule compliance?
   - MOI: is the Memorandum of Incorporation in place and current?
   - Beneficial ownership register (BOE): mandatory for all companies since 1 April 2023 — filed with CIPC?

2. BBBEE (Act 53 of 2003 + Codes of Good Practice)
   - Current level: {bbbee}
   - EME threshold: annual turnover <R10M → automatic Level 4 (or Level 1 if >51% black-owned)
   - QSE threshold: turnover R10M–R50M → report on best 4 of 5 elements
   - Large enterprise (>R50M): all 5 elements scored
   - For this business (revenue {revenue:,.0f}), what category applies?
   - Ownership element (25 pts): what % black ownership, voting rights, economic interest?
   - Management control (15 pts): board and senior management demographics
   - Skills development (25 pts): training spend as % of payroll (target 6%)
   - ESD (40 pts): preferential procurement from BEE suppliers; enterprise development spend
   - SED (5 pts): 1% of NPAT to beneficiary communities
   - Fronting risk: any indicators of non-genuine BEE compliance?
   - Specific risks for tender eligibility or major client requirements

3. POPIA (Act 4 of 2013)
   - Information Officer appointed and registered with the Information Regulator?
   - PAIA Manual published (mandatory for private bodies with >50 employees or on request)?
   - Data processing agreements with third-party processors?
   - Consent mechanisms for marketing communications (direct marketing opt-in)?
   - Cross-border data transfer safeguards?
   - Breach notification readiness (72-hour window)?
   - Maximum fine: R10M or 10% of annual turnover

4. LABOUR RELATIONS ACT 66 OF 1995
   - Written employment contracts for all staff (BCEA Section 29 mandatory)?
   - Disciplinary code and procedure documented?
   - Any retrenchment exposure (Section 189: 3+ staff = consulting obligation)?
   - Applicable bargaining council or sectoral determination for this industry?
   - CCMA exposure: potential unfair dismissal or unfair labour practice claims?

5. CONSUMER PROTECTION ACT (if business sells to consumers)
   - Returns policy compliant (CPA Section 56: 6-month implied warranty on goods)?
   - Prohibited conduct checklist (Sections 40-41): unconscionable conduct, false/misleading?
   - Fixed-term consumer contracts: 20-day cancellation right with reasonable penalty only?

6. CIPC STANDING
   - Annual return overdue? (Penalty: 10% of annual return fee per month)
   - Beneficial ownership register filed?
   - Company in good standing or deregistration risk?

For each issue, calculate the estimated maximum financial liability under the relevant act and state the specific remedy (form number, deadline, cost).
"""
        raw = self._call_claude(prompt)
        findings = self._parse_findings(raw, memory)

        # Set summary fields on memory
        if findings:
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            top = sorted(findings, key=lambda f: severity_order.get(f.severity, 0), reverse=True)
            memory.sa_legal_summary = f"{len(findings)} legal findings | Top: {top[0].title}" if top else ""
            risk_map = {"critical": 85, "high": 65, "medium": 40, "low": 20}
            memory.sa_legal_risk_score = risk_map.get(top[0].severity, 30) if top else 10
            # Build BBBEE analysis summary
            bbbee_findings = [f for f in findings if "bbbee" in f.title.lower() or "bee" in f.title.lower() or "bbbee" in f.detail.lower()]
            memory.sa_bbbee_analysis = {
                "declared_level": bbbee,
                "finding_count": len(bbbee_findings),
                "risk_flags": [f.title for f in bbbee_findings],
            }
        else:
            memory.sa_legal_summary = "No major legal compliance issues identified."
            memory.sa_legal_risk_score = 10
            memory.sa_bbbee_analysis = {"declared_level": bbbee, "finding_count": 0, "risk_flags": []}

        memory.sa_cipc_status = "unknown"
        memory.sa_legal_performed = True
        return findings


# ── Agent registry ───────────────────────────────────────────────────────────
# SATaxAgent and SALegalAgent are intentionally excluded — they run as
# dedicated phases 2c/2d in the CEO pipeline after market deep-dive so they
# can benefit from all prior findings context.
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
]
rent gross margin % (unless a specific improvement is identified)
- Opex: grow at 80% of revenue growth rate (partial operating leverage)
- Apply quick wins identified by other agents that are low risk and high probability
- Project month-by-month for 12 months
- Calculate: projected revenue, gross profit, operating profit, net profit, cash balance

BULL CASE (optimistic — 25% probability weight):
- Revenue: trend + 15% uplift (all quick wins implemented, market conditions favourable)
- Gross margin: improved to industry median (if currently below)
- Opex: flat or -5% (efficiency improvements)
- Working capital: debtor days reduced by 15 days

BEAR CASE (conservative — 25% probability weight):
- Revenue: trend - 10% (demand softness, competitive pressure, key customer loss)
- Gross margin: -2pp compression (cost pressure)
- Opex: sticky (cannot be cut quickly)
- Cash: model the cash impact of the revenue shortfall

For each scenario:
- State the 3 key assumptions driving it
- Project 12-month total revenue
- Project 12-month operating profit
- Identify the cash inflection point (when does cash run out in bear case?)
- State what triggers would move the business from base to bear

Also generate a monthly breakdown (12 rows) for the base case.

IMPORTANT: All projections must be explicitly labelled as projections, not forecasts or guarantees.
State the uncertainty range and the most critical assumption to monitor.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory) -> list:
        benchmark_block = self._build_benchmark_block(memory)
        cur = memory.currency
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA (use this as the historical baseline):
{json.dumps(business_data.get('financial', {}), indent=2)[:4000]}

ALL AGENT FINDINGS (incorporate improvements from quick wins in base/bull cases):
{memory.get_all_findings_text()[:2000]}

Build three 12-month forward scenarios using the methodology in your system prompt.
Show assumptions clearly.
State the most important number to watch each month.

End your analysis with a JSON block in this exact format:
{{
  "forecast_base_12m": <total projected revenue base case>,
  "forecast_bull_12m": <total projected revenue bull case>,
  "forecast_bear_12m": <total projected revenue bear case>,
  "forecast_assumptions": [
    "<assumption 1>",
    "<assumption 2>",
    "<assumption 3>"
  ],
  "forecast_monthly": [
    {{"month": "Month 1", "base": <number>, "bull": <number>, "bear": <number>}},
    {{"month": "Month 2", "base": <number>, "bull": <number>, "bear": <number>}}
  ]
}}
Include all 12 months in forecast_monthly.
"""
        raw = self._call_claude(prompt)

        # Extract structured forecast data
        import re
        # Find the JSON block — it may contain nested arrays
        json_match = re.search(r'\{[^{}]*"forecast_base_12m".*?\}(?=\s*$|\s*\n\s*[A-Z])', raw, re.DOTALL)
        if not json_match:
            # Broader search
            json_match = re.search(r'\{.*"forecast_base_12m".*\}', raw, re.DOTALL)
        if json_match:
            try:
                forecast_data = json.loads(json_match.group())
                memory.forecast_base_12m = float(forecast_data.get("forecast_base_12m", 0))
                memory.forecast_bull_12m = float(forecast_data.get("forecast_bull_12m", 0))
                memory.forecast_bear_12m = float(forecast_data.get("forecast_bear_12m", 0))
                memory.forecast_assumptions = forecast_data.get("forecast_assumptions", [])
                memory.forecast_monthly = forecast_data.get("forecast_monthly", [])
            except Exception:
                pass

        return self._parse_findings(raw, memory)


# Registry — used by CEO agent to dispatch all agents
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
    FraudDetectionAgent,
    CreditReadinessAgent,
    ValuationAgent,
    ForecastAgent,
]
