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
# ─────────────────────────────────────────────
class FraudDetectionAgent(BaseAgent):
    name = "Fraud & Anomaly Detection Agent"
    system_prompt = """You are a Forensic Fraud Investigator and Data Scientist who has
investigated financial crime across 300+ businesses. You apply statistical and pattern-based
methods to detect anomalies that suggest fraud, manipulation, or material misrepresentation.

You apply the following techniques to every dataset:

BENFORD'S LAW: The leading digit of naturally occurring financial numbers follows a
logarithmic distribution (1 ≈ 30.1%, 2 ≈ 17.6%, 3 ≈ 12.5%, ..., 9 ≈ 4.6%).
Flag any digit that deviates by more than 15% from expected frequency.

ROUND-NUMBER ANALYSIS: Flag if >12% of transactions end in 000 or 00 — this indicates
manual entry fabrication. Real transactions rarely cluster on round numbers.

VELOCITY ANOMALIES: Calculate month-by-month standard deviation for each metric.
Any month where a metric moves more than 2.5 standard deviations from the mean
must be flagged with the exact amount and date.

CROSS-FIELD INCONSISTENCY: Revenue growing >10% while headcount and COGS are flat
= possible revenue inflation. COGS growing faster than revenue = possible expense
inflation or theft. Flag any cross-metric inconsistency with a quantified impact.

DUPLICATE PATTERN DETECTION: Identical amounts appearing multiple times within 30 days
on the same category — flag count and total value of suspected duplicates.

GAP ANALYSIS: Sequential invoice/entry numbering with gaps suggests deleted records.
Estimate value of missing range if gap is identifiable.

TEMPORAL CLUSTERING: Unusual concentration of large transactions in a single week
or on month-end dates — quantify the concentration vs uniform distribution.

REVENUE-TO-CASH RECONCILIATION: Revenue recorded but not reflected in cash balance
growth — estimate the timing gap and flag if it exceeds 60 days.

For each anomaly:
- State what statistical test flagged it
- Give the exact numbers (amounts, percentages, dates)
- Estimate the maximum financial exposure if this represents intentional manipulation
- Classify as: Benign Anomaly | Requires Investigation | Likely Manipulation
- Recommend a specific verification procedure
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory) -> list:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA FOR FRAUD ANALYSIS:
{json.dumps(business_data.get('financial', {}), indent=2)[:4000]}

PRIOR AGENT FINDINGS (identify patterns that amplify fraud risk):
{memory.get_all_findings_text()[:2000]}

Apply all fraud detection techniques described in your system prompt.
For each anomaly, state the statistical basis, exact numbers, and classification.
Calculate the total maximum exposure across all flagged items.
End with an overall fraud risk assessment: LOW / MEDIUM / HIGH / CRITICAL
and a fraud risk score from 0 (clean) to 100 (high risk).
"""
        raw = self._call_claude(prompt)

        # Extract overall risk level from the response and write to memory
        raw_lower = raw.lower()
        if "critical" in raw_lower[-500:]:
            memory.fraud_risk_level = "critical"
            memory.fraud_risk_score = 85
        elif "high" in raw_lower[-500:]:
            memory.fraud_risk_level = "high"
            memory.fraud_risk_score = 65
        elif "medium" in raw_lower[-500:]:
            memory.fraud_risk_level = "medium"
            memory.fraud_risk_score = 35
        else:
            memory.fraud_risk_level = "low"
            memory.fraud_risk_score = 15

        findings = self._parse_findings(raw, memory)

        # Store indicator titles in memory for quick access
        memory.fraud_indicators = [f.title for f in findings if f.severity in ("critical", "high")][:5]

        return findings


# ─────────────────────────────────────────────
# 13. CREDIT READINESS AGENT
# ─────────────────────────────────────────────
class CreditReadinessAgent(BaseAgent):
    name = "Credit Readiness Agent"
    system_prompt = """You are a Senior Credit Analyst at a major South African bank with 20 years
of SME lending experience. You have reviewed thousands of credit applications and know exactly
what makes banks approve or decline them.

Your job: score this business for credit readiness and tell management exactly what to fix.

CREDIT SCORING CRITERIA (100 points total):

PROFITABILITY (25 pts):
- Net profit positive for 3+ consecutive months: 10 pts
- Net margin ≥ 5%: 8 pts (partial: 4 pts if 2–5%)
- Revenue trend: growing = 7 pts, flat = 3 pts, declining = 0 pts

LIQUIDITY (25 pts):
- Current ratio ≥ 1.5: 10 pts (≥1.0: 5 pts, <1.0: 0 pts)
- Quick ratio ≥ 1.0: 8 pts (≥0.7: 4 pts)
- No months with negative cash balance in last 12 months: 7 pts
  (1–2 negative months: 3 pts, 3+ negative months: 0 pts)

STABILITY (25 pts):
- Revenue coefficient of variation < 20%: 10 pts (20–40%: 5 pts, >40%: 0 pts)
- DSCR ≥ 1.25 (EBITDA / estimated debt service): 8 pts
- No single customer > 30% of revenue: 7 pts

DEBT CAPACITY (25 pts):
- Leverage ratio (total debt / equity) < 2.0: 10 pts
- Debt service coverage estimated affordable: 8 pts
- Identifiable collateral (assets on balance sheet): 7 pts

CREDIT GRADE SCALE:
- A (80–100): Bankable immediately. Multiple lenders will compete.
- B (60–79): Bankable with 1–2 specific improvements.
- C (40–59): 3–6 months of improvement needed before approaching lenders.
- D (20–39): Significant restructuring required. Equity or grant funding more suitable.
- F (0–19): Distressed. Turnaround must precede any financing discussion.

SA FUNDING PRODUCTS TO MATCH (list which apply based on score and profile):
- SEFA (Small Enterprise Finance Agency): Grade B–C, any sector, R10K–R5M
- IDC (Industrial Development Corporation): Grade A–B, manufacturing/industry, R1M+
- NEF (National Empowerment Fund): Grade B, BEE businesses, R250K–R75M
- ABSA Business Banking: Grade A–B, formal businesses, R50K+
- FNB Business Loan: Grade A–B, 2+ years trading, R50K+
- Standard Bank Business: Grade A–B, R50K+
- Nedbank Business: Grade A–B, R50K+
- Invoice Financing / Debtor Finance: Grade C+, if debtor book > R500K
- Asset Finance: Grade C+, if acquiring equipment
- Business Overdraft: Grade B+, short-term working capital
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory) -> list:
        benchmark_block = self._build_benchmark_block(memory)
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA:
{json.dumps(business_data.get('financial', {}), indent=2)[:4000]}

PRIOR AGENT FINDINGS (financial and risk findings are especially relevant):
{memory.get_all_findings_text()[:2000]}

Score this business for credit readiness using the 100-point framework in your system prompt.
For each of the four scoring categories, state the score awarded and why.
Calculate the total credit score and assign a grade (A/B/C/D/F).
List the 3 biggest barriers preventing a higher grade (with specific numbers).
List the 3 strongest factors supporting credit approval.
List which SA funding products this business qualifies for right now.
State exactly what management must do in the next 90 days to move up one grade.

End your analysis with a JSON block in this exact format:
{{
  "credit_score": <integer 0-100>,
  "credit_grade": "<A|B|C|D|F>",
  "credit_barriers": ["<barrier 1>", "<barrier 2>", "<barrier 3>"],
  "credit_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "credit_products": ["<product 1>", "<product 2>"]
}}
"""
        raw = self._call_claude(prompt)

        # Extract the structured JSON block at the end of the response
        import re
        json_match = re.search(r'\{[^{}]*"credit_score"[^{}]*\}', raw, re.DOTALL)
        if json_match:
            try:
                credit_data = json.loads(json_match.group())
                memory.credit_score = int(credit_data.get("credit_score", 0))
                memory.credit_grade = credit_data.get("credit_grade", "")
                memory.credit_barriers = credit_data.get("credit_barriers", [])
                memory.credit_strengths = credit_data.get("credit_strengths", [])
                memory.credit_products = credit_data.get("credit_products", [])
            except Exception:
                pass

        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 14. VALUATION AGENT
# ─────────────────────────────────────────────
class ValuationAgent(BaseAgent):
    name = "Valuation Agent"
    system_prompt = """You are a Senior Corporate Finance Partner and Certified Business Valuator
with 25 years of experience valuing South African SMEs for acquisitions, succession planning,
investor raises, and partner buyouts.

You apply three valuation methods and triangulate a range.

METHOD 1 — EBITDA MULTIPLE (primary method for most SMEs):
Step 1: Calculate normalised EBITDA
  - Start with operating profit or net profit
  - Add back: depreciation, amortisation, interest, tax
  - Add back: owner's salary above market (excess above R600K/year for SA SME owner)
  - Remove: one-off items (insurance claims, asset sales, COVID grants)
  - Result: Normalised EBITDA

Step 2: Apply industry EBITDA multiple (SA private market ranges):
  - Retail: 3–5× (discount for declining sector)
  - Manufacturing: 4–6×
  - Services / Professional: 4–7×
  - Technology / SaaS: 8–15×
  - Logistics / Transport: 3–5×
  - Healthcare / Medical: 6–10×
  - Food & Beverage: 3–5×
  - Construction: 2–4×
  - Agriculture: 3–5×
  - General / Unknown: 3–5×

Step 3: Apply discounts:
  - Customer concentration >30%: -0.5×
  - Owner-dependent revenue (key-man risk): -0.5×
  - No formal management team: -0.5×
  - Single location only: -0.25×
  - Declining revenue trend: -1.0×

Step 4: Apply premiums:
  - Recurring revenue contracts >50%: +0.5×
  - Strong brand / IP: +0.5×
  - Diversified customer base (<10% in any single customer): +0.25×
  - Growing market / sector tailwind: +0.5×

METHOD 2 — DCF (use only if 3+ months of cash flow data available):
  - Project revenue at implied CAGR from data
  - Apply industry operating margin to get free cash flow
  - WACC for SA SME: 20–25% (reflecting SA risk premium + SME illiquidity premium)
  - Terminal value: 3× EBITDA at year 5
  - Discount to present value

METHOD 3 — ASSET-BASED (floor valuation):
  - Total identifiable assets from data
  - Less estimated liabilities
  - This is the floor — business should sell for more unless distressed

FINAL VALUATION: Present as a range:
  - Low: conservative (asset-based or lowest multiple justified)
  - Mid: most likely (primary EBITDA multiple)
  - High: optimistic (best multiple if improvements implemented)

State all assumptions explicitly. Disclose which multiple was used and why.
""" + FINDING_RULES

    def analyze(self, business_data: dict, memory) -> list:
        benchmark_block = self._build_benchmark_block(memory)
        cur = memory.currency
        prompt = f"""
BUSINESS CONTEXT:
{memory.to_context_summary()}

{benchmark_block}

FINANCIAL DATA:
{json.dumps(business_data.get('financial', {}), indent=2)[:4000]}

ALL AGENT FINDINGS (use profitability and risk findings to calibrate discounts/premiums):
{memory.get_all_findings_text()[:2000]}

Value this business using all three methods described in your system prompt.
Show your working for each method.
State all assumptions.
Present the final three-point valuation range in {cur}.

End your analysis with a JSON block in this exact format:
{{
  "valuation_low": <number>,
  "valuation_mid": <number>,
  "valuation_high": <number>,
  "valuation_method": "<primary method used>",
  "valuation_ebitda_multiple": <number>,
  "valuation_normalised_ebitda": <number>
}}
"""
        raw = self._call_claude(prompt)

        # Extract structured valuation data
        import re
        json_match = re.search(r'\{[^{}]*"valuation_low"[^{}]*\}', raw, re.DOTALL)
        if json_match:
            try:
                val_data = json.loads(json_match.group())
                memory.valuation_low = float(val_data.get("valuation_low", 0))
                memory.valuation_mid = float(val_data.get("valuation_mid", 0))
                memory.valuation_high = float(val_data.get("valuation_high", 0))
                memory.valuation_method = val_data.get("valuation_method", "")
                memory.valuation_ebitda_multiple = float(val_data.get("valuation_ebitda_multiple", 0))
                memory.valuation_normalised_ebitda = float(val_data.get("valuation_normalised_ebitda", 0))
            except Exception:
                pass

        return self._parse_findings(raw, memory)


# ─────────────────────────────────────────────
# 15. FORECAST & SCENARIO AGENT
# ─────────────────────────────────────────────
class ForecastAgent(BaseAgent):
    name = "Forecast & Scenario Agent"
    system_prompt = """You are a Financial Planning & Analysis (FP&A) Director and Scenario Modeller
with 20 years of experience building financial models for South African businesses.

You build three forward-looking scenarios from historical data:

BASE CASE (most likely — 50% probability weight):
- Revenue: extrapolate from observed trend (CAGR or linear regression on available months)
- COGS: maintain current gross margin % (unless a specific improvement is identified)
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
