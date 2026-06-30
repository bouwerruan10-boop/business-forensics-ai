"""
Shared Memory -- the single source of truth across all agents.
Every specialist agent reads from and writes to this object.
"""

import math
from dataclasses import dataclass, field


def _finite_float(v):
    """Coerce to a finite float; non-numeric / inf / nan -> 0.0."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def _finite_nonneg_int(v):
    """Coerce to a non-negative int; non-numeric / inf / nan / negative -> 0."""
    f = _finite_float(v)
    return int(f) if f > 0 else 0


@dataclass
class AgentFinding:
    agent: str
    category: str
    severity: str            # critical | high | medium | low
    title: str
    detail: str
    financial_impact: str
    recommendation: str
    roi_estimate: str
    cost_of_inaction: str = ""
    benchmark_reference: str = ""
    data_source: str = ""
    evidence_plain_language: str = ""   # plain-English "what we found / from where / why it matters"
    quick_win: bool = False
    verification: str = ""        # "" | "confirmed" | "conflict" (vs computed ratios)
    verification_note: str = ""
    prose_check: str = ""         # "" | "conflict" (qualitative narrative vs computed ratio status)
    prose_note: str = ""


@dataclass
class SharedMemory:
    # Business identity (pre-populated from profile form)
    business_name: str = "Unknown Business"
    industry: str = ""
    industry_key: str = "general"
    annual_revenue: float = 0.0
    headcount: int = 0
    currency: str = "USD"
    country: str = ""

    # Parsed data
    revenue_streams: list = field(default_factory=list)
    cost_centers: list = field(default_factory=list)

    # Intelligence
    findings: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)

    # Health scores (set by CEO agent)
    business_health_score: int = 0
    profitability_score: int = 0
    efficiency_score: int = 0
    risk_score: int = 0

    # Deterministic financial ratios — computed from uploaded financials, NOT LLM-generated
    financial_figures: dict = field(default_factory=dict)     # extracted line items
    financial_extraction_source: str = ""   # "deterministic" | "ai" — provenance of the figures
    financial_ratios: dict = field(default_factory=dict)      # {key: {value, benchmark, status, source}}
    financial_fundamentals_score: int = 0                     # 0-100 (0 = not computed)

    # Phase 1 — faithfulness verification (findings vs computed ratios)
    faithfulness_summary: dict = field(default_factory=dict)   # {checked, confirmed, conflicts, conflict_titles}
    prose_verifier_summary: dict = field(default_factory=dict) # {checked, flagged, flag_titles}
    # Phase 0 — observability
    agent_timings: list = field(default_factory=list)          # [{agent, seconds}]
    total_runtime_seconds: float = 0.0

    # Imara Score (branded composite, set by CEO agent Phase 4)
    imara_score: int = 0                     # 0-100 bankability / investability
    imara_band: str = ""                     # "A" | "B" | "C" | "D" | "E"
    imara_label: str = ""                    # e.g. "Investment Ready"
    imara_components: list = field(default_factory=list)  # [{label, value, weight}]
    imara_color: str = ""                    # canonical band hex (single source of truth)
    imara_completeness: int = 0              # 0-100: how many components were produced
    imara_confidence: str = "low"            # "high" | "medium" | "low"

    # Client context
    primary_concern: str = ""   # client's stated focus area from profile form
    business_context: str = ""  # extra narrative context about the business / its current state

    # Business model context
    business_model_summary: str = ""
    key_risks: list = field(default_factory=list)
    key_opportunities: list = field(default_factory=list)

    # ── New agent outputs ─────────────────────────────────────────

    # Fraud & Anomaly Detection
    fraud_risk_level: str = "unknown"        # "low" | "medium" | "high" | "critical"
    fraud_risk_score: int = 0                # 0-100  (100 = highest risk)
    fraud_indicators: list = field(default_factory=list)

    # Credit Readiness
    credit_score: int = 0                    # 0-100 credit readiness score
    credit_source: str = "model"             # "model" (credit agent) | "derived" (CEO fallback)
    credit_grade: str = ""                   # "A" | "B" | "C" | "D" | "F"
    credit_barriers: list = field(default_factory=list)
    credit_strengths: list = field(default_factory=list)
    credit_products: list = field(default_factory=list)  # funding products available

    # Valuation
    valuation_low: float = 0.0
    valuation_mid: float = 0.0
    valuation_high: float = 0.0
    valuation_method: str = ""               # e.g. "EBITDA Multiple + DCF"
    valuation_ebitda_multiple: float = 0.0
    valuation_normalised_ebitda: float = 0.0

    # Forecast & Scenario
    forecast_base_12m: float = 0.0           # base-case 12-month revenue
    forecast_bull_12m: float = 0.0           # bull-case
    forecast_bear_12m: float = 0.0           # bear-case
    forecast_assumptions: list = field(default_factory=list)
    forecast_monthly: list = field(default_factory=list)  # [{month, base, bull, bear}]

    # ── Market Research ───────────────────────────────────────────
    market_visibility_score: int = 0         # 0-100 (0 = no online presence)
    market_sentiment: str = "unknown"        # "positive" | "neutral" | "negative" | "unknown"
    market_news: list = field(default_factory=list)       # [{title, url, source, snippet, date}]
    market_competitors: list = field(default_factory=list) # [str] competitor names
    market_opportunities: list = field(default_factory=list) # [str] market opportunities
    market_risks: list = field(default_factory=list)      # [str] market-level risks
    market_context_summary: str = ""         # compact string injected into specialist agent prompts
    market_search_performed: bool = False    # True once quick scan has run
    market_total_results: int = 0            # total search results found across all queries

    # ── SA Intake Profile Fields ──────────────────────────────────
    entity_type: str = ""                    # Pty Ltd / CC / Sole Prop / Trust / NPO / etc.
    cipc_number: str = ""                    # CIPC registration number e.g. 2015/123456/07
    vat_registered: str = "unknown"          # "yes" | "no" | "pending" | "unknown"
    vat_number: str = ""                     # VAT vendor number (10 digits)
    tax_year_end: str = ""                   # e.g. "February" | "June" | "December"
    years_in_business: str = ""              # e.g. "1-3 years" | "3-7 years"
    bbbee_level: str = ""                    # e.g. "Level 1" | "Exempt" | "Non-Compliant"
    banking_partner: str = ""                # Primary bank e.g. "Standard Bank"
    report_audience: str = "owner"           # "owner" | "banker" | "investor"

    # ── Document Category Text Buckets ────────────────────────────
    # Each specialist agent reads from its own bucket
    uploaded_financial_text: str = ""        # income statement, balance sheet, management accounts
    uploaded_bank_text: str = ""             # bank statements 3-6 months
    uploaded_tax_text: str = ""              # VAT201, IT14, EMP201, IRP6, tax clearance
    uploaded_legal_text: str = ""            # MOI, shareholder agreements, contracts
    uploaded_hr_text: str = ""               # payroll, employment contracts, leave records
    uploaded_plan_text: str = ""             # business plan

    # ── SA Tax Agent Outputs ──────────────────────────────────────
    sa_tax_risk_score: int = 0               # 0-100 (100 = highest tax risk)
    sa_tax_summary: str = ""                 # injected into CEO synthesis
    sa_vat_status: str = "unknown"           # "compliant" | "risk" | "unknown"
    sa_tax_clearance_status: str = "unknown" # "valid" | "expired" | "not_provided" | "unknown"
    sa_tax_performed: bool = False           # True once SATaxAgent has run

    # SA Tax Optimisation (legal planning; "Tax Me If You Can").
    # tax_opt_summary feeds to_context_summary(); the full dict is serialised into the report.
    # (The unread total_low / total_high / performed scalar mirrors were removed.)
    tax_opt_summary: str = ""
    tax_optimization: dict = field(default_factory=dict)

    # SA structural tax-risk flags (GAAR ss80A-80L / SARS scrutiny) — the mirror of
    # tax_optimization. tax_risk_summary feeds to_context_summary(); the full dict is
    # serialised into the report.
    tax_risk_summary: str = ""
    tax_risk_flags: dict = field(default_factory=dict)

    # ── SA Legal Agent Outputs ────────────────────────────────────
    sa_legal_risk_score: int = 0             # 0-100 (100 = highest legal risk)
    sa_legal_summary: str = ""               # injected into CEO synthesis
    sa_bbbee_analysis: dict = field(default_factory=dict)  # level, elements, risk flags
    sa_cipc_status: str = "unknown"          # "compliant" | "overdue" | "unknown"
    sa_legal_performed: bool = False         # True once SALegalAgent has run

    # ── Economics / Macro Agent Outputs ───────────────────────────
    macro_performed: bool = False            # True once EconomicsAgent has run
    macro_summary: str = ""                  # injected into CEO synthesis
    macro_overall_exposure: str = ""         # low | medium | high
    macro_top_driver: str = ""               # the macro factor the firm is most exposed to
    macro_sensitivity: dict = field(default_factory=dict)  # per-driver exposure profile

    # Identity + document fields that MUST be their declared type: a downstream
    # consumer doing memory.country.strip() / .lower() / an f-string format-spec must
    # never meet an int/dict/None from a hostile profile or direct construction.
    _STR_FIELDS = (
        "business_name", "industry", "industry_key", "currency", "country",
        "entity_type", "vat_registered", "vat_number", "tax_year_end",
        "years_in_business", "bbbee_level", "banking_partner", "report_audience",
        "primary_concern", "business_context",
        "uploaded_financial_text", "uploaded_bank_text", "uploaded_tax_text",
        "uploaded_legal_text", "uploaded_hr_text", "uploaded_plan_text",
    )

    def __post_init__(self):
        # Normalise identity fields at the single source of truth so NO downstream
        # consumer (f-strings like {rev:,.0f}, comparisons, .strip()/.lower(), JSON
        # output) can ever see a wrong-typed or non-finite value — a hostile "1e400"
        # (-> inf), "twelve", or a dict/int would otherwise crash the pipeline.
        self.annual_revenue = _finite_float(self.annual_revenue)
        self.headcount = _finite_nonneg_int(self.headcount)
        for _f in self._STR_FIELDS:
            v = getattr(self, _f)
            if not isinstance(v, str):
                setattr(self, _f, "" if v is None else str(v))

    def add_finding(self, finding):
        self.findings.append(finding)

    def post_message(self, from_agent, to_agent, message):
        self.messages.append({"from": from_agent, "to": to_agent, "message": message})

    def get_findings_by_severity(self, severity):
        return [f for f in self.findings if f.severity == severity]

    def get_quick_wins(self):
        return [f for f in self.findings if f.quick_win]

    def get_all_findings_text(self):
        if not self.findings:
            return "No findings recorded yet."
        lines = []
        for finding in self.findings:
            lines.append(
                f"[{finding.severity.upper()}] {finding.title} ({finding.agent}): "
                f"{finding.detail} | Impact: {finding.financial_impact} | "
                f"Recommendation: {finding.recommendation}"
            )
        return "\n".join(lines)

    def to_context_summary(self):
        """Compact summary injected into CEO synthesis prompt."""
        parts = [
            f"Business: {self.business_name} | Industry: {self.industry} | "
            f"Revenue: {self.currency} {self.annual_revenue:,.0f} | Headcount: {self.headcount}",
            f"Health: {self.business_health_score}/100 | "
            f"Profitability: {self.profitability_score}/100 | "
            f"Efficiency: {self.efficiency_score}/100 | "
            f"Risk: {self.risk_score}/100",
            f"Total findings: {len(self.findings)} "
            f"(Critical: {len(self.get_findings_by_severity('critical'))}, "
            f"High: {len(self.get_findings_by_severity('high'))})",
        ]
        if self.primary_concern:
            parts.append(f"Primary concern: {self.primary_concern}")
        if self.business_context:
            parts.append(f"Business context: {self.business_context}")
        if self.business_model_summary:
            parts.append(f"Business model: {self.business_model_summary}")
        if self.market_context_summary:
            parts.append(f"Market context: {self.market_context_summary}")
        if self.entity_type:
            parts.append(f"Entity: {self.entity_type} | BBBEE: {self.bbbee_level or 'unknown'} | VAT: {self.vat_registered}")
        if self.sa_tax_summary:
            parts.append(f"SA Tax: {self.sa_tax_summary}")
        if self.tax_opt_summary:
            parts.append(f"Tax Me If You Can (legal tax saving): {self.tax_opt_summary}")
        if self.tax_risk_summary:
            parts.append(f"Structural tax-risk (GAAR/SARS): {self.tax_risk_summary}")
        if self.sa_legal_summary:
            parts.append(f"SA Legal: {self.sa_legal_summary}")
        return "\n".join(parts)
