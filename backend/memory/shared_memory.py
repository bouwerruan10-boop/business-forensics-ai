"""
Shared Memory -- the single source of truth across all agents.
Every specialist agent reads from and writes to this object.
"""

from dataclasses import dataclass, field
import json


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
    quick_win: bool = False


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
    raw_data: dict = field(default_factory=dict)
    revenue_streams: list = field(default_factory=list)
    cost_centers: list = field(default_factory=list)
    departments: list = field(default_factory=list)

    # Intelligence
    findings: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)

    # Health scores (set by CEO agent)
    business_health_score: int = 0
    profitability_score: int = 0
    efficiency_score: int = 0
    risk_score: int = 0

    # Client context
    primary_concern: str = ""   # client's stated focus area from profile form

    # Business model context
    business_model_summary: str = ""
    key_risks: list = field(default_factory=list)
    key_opportunities: list = field(default_factory=list)

    # ── New agent outputs ─────────────────────────────────────────

    # Fraud & Anomaly Detection
    fraud_risk_level: str = "unknown"        # "low" | "medium" | "high" | "critical"
    fraud_risk_score: int = 0                # 0–100  (100 = highest risk)
    fraud_indicators: list = field(default_factory=list)

    # Credit Readiness
    credit_score: int = 0                    # 0–100 credit readiness score
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

    def add_finding(self, finding):
        self.findings.append(finding)

    def post_message(self, from_agent, to_agent, message):
        self.messages.append({"from": from_agent, "to": to_agent, "message": message})

    def get_findings_by_agent(self, agent_name):
        return [f for f in self.findings if f.agent == agent_name]

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
                "[" + finding.severity.upper() + "] " + finding.agent + " -- " + finding.title + "\n"
                "  Financial Impact: " + finding.financial_impact + "\n"
                "  Benchmark: " + finding.benchmark_reference + "\n"
                "  Recommendation: " + finding.recommendation
            )
        return "\n".join(lines)

    def to_context_summary(self) -> str:
        """Return a compact string for injecting into agent prompts."""
        parts = [
            "Business: " + self.business_name,
            "Industry: " + (self.industry or self.industry_key),
            "Revenue: " + self.currency + " " + "{:,.0f}".format(self.annual_revenue),
            "Headcount: " + str(self.headcount),
            "Findings so far: " + str(len(self.findings)),
        ]
        if self.primary_concern:
            parts.append("Client concern: " + self.primary_concern)
        return "  |  ".join(parts)
