"""
CEO Agent — orchestrates all specialist agents, synthesises cross-agent findings,
and generates the final premium consulting report structure.

Narrative arc: Situation → Complication → Resolution (McKinsey SCR)
Findings ranked by quantified financial impact, not by agent order.
"""
import json
import re
from agents.base_agent import BaseAgent
from agents.specialist_agents import ALL_AGENTS, SATaxAgent, SALegalAgent
from agents.market_research_agent import MarketResearchAgent, MarketDeepDiveAgent
from memory.shared_memory import SharedMemory, AgentFinding
from config import MODEL, MAX_TOKENS


class CEOAgent(BaseAgent):
    name = "CEO Agent"
    system_prompt = """You are the Chief Executive AI Consultant of a world-class management
consulting firm. You lead a team of 11 specialist agents. Your role is to:

- Coordinate and orchestrate specialist investigations
- Synthesise all findings into a coherent strategic narrative
- Resolve conflicts and contradictions between agent recommendations
- Rank every finding by quantified financial impact — most expensive problem first
- Identify systemic root causes that span multiple departments
- Separate quick wins (< 30 days) from medium-term and strategic initiatives
- Generate board-ready, McKinsey-quality output

You communicate with authority, precision, and commercial urgency.
Every conclusion is anchored to specific numbers from the data, compared against
real industry benchmarks. You never pad, never hedge without data, never use
generic business language."""

    def run_full_analysis(
        self,
        business_data: dict,
        memory: SharedMemory,
        progress_callback=None
    ) -> dict:
        """
        Full multi-agent analysis pipeline.
        Phase 1: Business model extraction
        Phase 2: Specialist agents (11 agents, sequential)
        Phase 3: Cross-agent synthesis
        Phase 4: Scoring
        Phase 5: Final report generation
        """

        # Phase 1: Business model — profile data takes priority over extracted data
        if progress_callback:
            progress_callback("CEO Agent", "Analysing business model from uploaded data...")
        self._build_business_model(business_data, memory)

        # Phase 1b: Market quick scan — runs first so all specialists get market context
        if progress_callback:
            progress_callback("Market Research Agent", "Scanning market presence and industry trends...")
        market_scout = MarketResearchAgent()
        market_scout.analyze(business_data, memory)

        # Phase 2: Specialist agents (now enriched with market_context_summary)
        for AgentClass in ALL_AGENTS:
            agent = AgentClass()
            if progress_callback:
                progress_callback(agent.name, f"{agent.name} conducting investigation...")
            findings = agent.analyze(business_data, memory)
            for f in findings:
                memory.add_finding(f)

        # Phase 2b: Market deep dive — full intelligence after all specialists
        if progress_callback:
            progress_callback("Market Intelligence Agent", "Conducting deep market research and competitor analysis...")
        market_deep = MarketDeepDiveAgent()
        market_findings = market_deep.analyze(business_data, memory)
        for f in market_findings:
            memory.add_finding(f)

        # Phase 2c: SA Tax Compliance Agent
        if progress_callback:
            progress_callback("SA Tax Compliance Agent", "Reviewing SARS tax obligations — VAT, CIT, PAYE, provisional tax...")
        sa_tax = SATaxAgent()
        sa_tax_findings = sa_tax.analyze(business_data, memory)
        for f in sa_tax_findings:
            memory.add_finding(f)

        # Phase 2d: SA Corporate Law & BBBEE Agent
        if progress_callback:
            progress_callback("SA Corporate Law & BBBEE Agent", "Reviewing Companies Act, BBBEE, POPIA, CIPC compliance...")
        sa_legal = SALegalAgent()
        sa_legal_findings = sa_legal.analyze(business_data, memory)
        for f in sa_legal_findings:
            memory.add_finding(f)

        # Phase 3: Cross-agent synthesis
        if progress_callback:
            progress_callback("CEO Agent", "Synthesising cross-agent findings...")
        synthesis = self._cross_agent_synthesis(memory)

        # Phase 4: Score the business
        if progress_callback:
            progress_callback("CEO Agent", "Calculating business health scores...")
        self._score_business(memory)
        self._calculate_imara_score(memory)

        # Phase 5: Generate report
        if progress_callback:
            progress_callback("CEO Agent", "Writing executive narrative...")
        report = self._generate_report(business_data, memory, synthesis)

        return report

    # ── Phase 1 ──────────────────────────────────────────────────

    def _build_business_model(self, business_data: dict, memory: SharedMemory):
        """
        Extract business structure from raw data.
        Profile fields provided by user (annual_revenue, headcount, currency, industry_key)
        take priority — we only use extracted values to fill gaps.
        """
        concern_line = (
            f"- Client's primary concern: \"{memory.primary_concern}\""
            if memory.primary_concern else ""
        )
        prompt = f"""
Analyse this raw business data and extract the business structure.

IMPORTANT: The business profile below was provided by the client. Use these as your
ground truth and do not contradict them. Only use data extraction to fill in
fields that are missing (0 or empty).

Known profile:
- Business name: {memory.business_name}
- Industry: {memory.industry or memory.industry_key}
- Annual revenue: {memory.annual_revenue} (0 = unknown, extract from data)
- Headcount: {memory.headcount} (0 = unknown, extract from data)
- Currency: {memory.currency}
- Country: {memory.country}
{concern_line}

Return a JSON object with these keys:
{{
  "business_name": "string — use profile value unless clearly wrong",
  "industry": "string — human-readable industry name",
  "annual_revenue": number,
  "headcount": number,
  "currency": "string e.g. ZAR or USD",
  "revenue_streams": [{{"name": "...", "estimated_annual_value": number}}],
  "cost_centers": [{{"name": "...", "estimated_annual_cost": number}}],
  "departments": ["string"],
  "business_model_summary": "2-3 sentence summary of how this business makes money",
  "key_risks": ["string"],
  "key_opportunities": ["string"]
}}

Raw business data (truncated to 4000 chars):
{json.dumps({k: str(v)[:500] for k, v in business_data.items()}, indent=2)[:4000]}

Return ONLY valid JSON. No explanation.
"""
        raw = self._call_claude(prompt)
        raw = _strip_json(raw)

        try:
            model = json.loads(raw)
            # Only update name/industry unconditionally
            if model.get("business_name") and model["business_name"] != "Unknown Business":
                memory.business_name = model["business_name"]
            if model.get("industry"):
                memory.industry = model["industry"]

            # Only fill numeric gaps — never overwrite profile-provided values
            if memory.annual_revenue == 0 and model.get("annual_revenue", 0) > 0:
                memory.annual_revenue = float(model["annual_revenue"])
            if memory.headcount == 0 and model.get("headcount", 0) > 0:
                memory.headcount = int(model["headcount"])

            # Non-conflicting fields — always set from extraction
            memory.revenue_streams = model.get("revenue_streams", [])
            memory.cost_centers = model.get("cost_centers", [])
            memory.departments = model.get("departments", [])
            memory.business_model_summary = model.get("business_model_summary", "")
            memory.key_risks = model.get("key_risks", [])
            memory.key_opportunities = model.get("key_opportunities", [])
        except Exception:
            # Extraction failed — profile data already on memory, continue
            pass

    # ── Phase 3 ──────────────────────────────────────────────────

    def _cross_agent_synthesis(self, memory: SharedMemory) -> dict:
        """
        Synthesise findings across all agents.
        Returns structured synthesis dict used in report generation.
        """
        cur = memory.currency
        rev = memory.annual_revenue

        concern_block = (
            f"\nCLIENT'S PRIMARY CONCERN: \"{memory.primary_concern}\"\n"
            "Your synthesis MUST directly address this concern. If the findings confirm it, "
            "quantify it precisely. If the data reveals a different root cause, explain why.\n"
            if memory.primary_concern else ""
        )
        prompt = f"""
You are the Chief Executive AI Consultant reviewing findings from 15 specialist agents
for {memory.business_name} (industry: {memory.industry}, annual revenue: {cur} {rev:,.0f}).

CREDIT READINESS: Score {memory.credit_score}/100 — Grade {memory.credit_grade}
ESTIMATED VALUATION: {cur} {memory.valuation_low:,.0f} — {cur} {memory.valuation_high:,.0f} (mid: {cur} {memory.valuation_mid:,.0f})
FRAUD RISK LEVEL: {memory.fraud_risk_level.upper()}
12-MONTH REVENUE FORECAST (base case): {cur} {memory.forecast_base_12m:,.0f}
{concern_block}
Your task: synthesise all findings into a coherent strategic picture.

━━━ ALL AGENT FINDINGS ━━━
{memory.get_all_findings_text()[:6000]}

Return a JSON object:
{{
  "situation": "2-3 sentences: what is this business, what markets does it serve, what are its revenue drivers?",
  "complication": "2-3 sentences: what is the core strategic problem revealed by the data? What is the root cause?",
  "resolution": "2-3 sentences: what is the single most important intervention and expected outcome?",
  "systemic_themes": [
    {{
      "theme": "e.g. Working capital crisis driven by debtor and inventory mismanagement",
      "agents_involved": ["Financial Forensics Agent", "Operations Agent"],
      "combined_impact": "{cur} X per year",
      "narrative": "2 sentence explanation"
    }}
  ],
  "top_priority_issues": [
    {{
      "rank": 1,
      "title": "...",
      "category": "...",
      "why_critical": "One paragraph — specific numbers, benchmarks, cost of inaction",
      "estimated_total_impact": "{cur} X per year",
      "owner": "which specialist agent found this",
      "quick_win": true/false
    }}
  ],
  "quick_wins_narrative": "1 paragraph describing all quick wins collectively and their combined 30-day impact",
  "strategic_plays_narrative": "1 paragraph describing the medium-term strategic programme"
}}

Include at least 5 items in top_priority_issues. Rank strictly by estimated_total_impact (largest first).
Return ONLY valid JSON.
"""
        raw = self._call_claude(prompt)
        raw = _strip_json(raw)
        try:
            synthesis = json.loads(raw)
            memory.post_message("CEO", "All Agents", json.dumps(synthesis))
            return synthesis
        except Exception:
            return {}

    # ── Phase 4 ──────────────────────────────────────────────────

    def _score_business(self, memory: SharedMemory):
        """
        Calculate four health scores (0–100).
        Weights by financial impact where possible.
        """
        findings = memory.findings
        if not findings:
            memory.business_health_score = 70
            memory.profitability_score = 70
            memory.efficiency_score = 70
            memory.risk_score = 70
            return

        def _sev_weight(f: AgentFinding) -> float:
            return {"critical": 15, "high": 8, "medium": 3, "low": 1}.get(f.severity, 3)

        total_penalty = sum(_sev_weight(f) for f in findings)
        base = max(15, 100 - total_penalty)

        financial_agents = {"Financial Forensics Agent", "Accounting Agent", "Procurement Agent"}
        ops_agents = {"Operations Agent", "Logistics Agent", "Human Resources Agent", "Sales Agent"}
        risk_agents = {"Auditor Agent", "Legal Risk Agent", "Fraud & Anomaly Detection Agent"}
        credit_agents = {"Credit Readiness Agent"}

        fin_findings = [f for f in findings if f.agent in financial_agents]
        ops_findings = [f for f in findings if f.agent in ops_agents]
        risk_findings = [f for f in findings if f.agent in risk_agents]
        credit_findings = [f for f in findings if f.agent in credit_agents]

        fin_penalty = sum(_sev_weight(f) for f in fin_findings)
        ops_penalty = sum(_sev_weight(f) for f in ops_findings)
        risk_penalty = sum(_sev_weight(f) for f in risk_findings)
        credit_penalty = sum(_sev_weight(f) for f in credit_findings)

        memory.profitability_score = min(100, max(10, 100 - fin_penalty))
        memory.efficiency_score = min(100, max(10, 100 - ops_penalty))
        memory.risk_score = min(100, max(10, 100 - int((risk_penalty + credit_penalty) / 2)))

        # Derive credit_grade from credit_score if the agent already set it
        if memory.credit_score == 0:
            # Fallback: estimate from financial health
            memory.credit_score = min(100, max(5, int(memory.profitability_score * 0.6 + memory.risk_score * 0.4)))
        if not memory.credit_grade:
            s = memory.credit_score
            memory.credit_grade = "A" if s >= 80 else "B" if s >= 60 else "C" if s >= 40 else "D" if s >= 20 else "F"

        memory.business_health_score = min(100, max(10, int(
            (memory.profitability_score + memory.efficiency_score + memory.risk_score) / 3
        )))

    def _calculate_imara_score(self, memory: SharedMemory):
        """
        Imara Score™ — a single branded 0–100 bankability / investability rating.

        Blends the agent outputs already produced, weighted toward what a lender
        or investor cares about. Components that were not produced this run (e.g.
        no market scan, no SA compliance pass, no credit assessment) are dropped
        and the remaining weights are re-normalised, so the score is always 0–100.
        """
        # (label, value 0-100 where higher = better, base weight, include?)
        candidates = [
            ("Profitability",        memory.profitability_score,            0.25, memory.profitability_score > 0),
            ("Credit Readiness",     memory.credit_score,                   0.20, memory.credit_score > 0),
            ("Risk & Compliance",    memory.risk_score,                     0.15, memory.risk_score > 0),
            ("Operational Efficiency", memory.efficiency_score,             0.10, memory.efficiency_score > 0),
            ("Financial Integrity",  100 - memory.fraud_risk_score,         0.10, memory.fraud_risk_level not in ("", "unknown")),
            ("Market Visibility",    memory.market_visibility_score,        0.10, bool(memory.market_search_performed)),
            ("Tax Compliance",       100 - memory.sa_tax_risk_score,        0.05, bool(memory.sa_tax_performed)),
            ("Legal Compliance",     100 - memory.sa_legal_risk_score,      0.05, bool(memory.sa_legal_performed)),
        ]

        active = [(label, value, weight) for (label, value, weight, include) in candidates if include]

        # Fallback: if nothing scored, anchor on business health
        if not active:
            active = [("Business Health", memory.business_health_score or 50, 1.0)]

        total_weight = sum(w for (_, _, w) in active)
        composite = sum(max(0, min(100, v)) * w for (_, v, w) in active) / total_weight

        memory.imara_score = int(round(max(0, min(100, composite))))

        s = memory.imara_score
        if s >= 80:
            memory.imara_band, memory.imara_label = "A", "Investment Ready"
        elif s >= 65:
            memory.imara_band, memory.imara_label = "B", "Bankable"
        elif s >= 50:
            memory.imara_band, memory.imara_label = "C", "Developing"
        elif s >= 35:
            memory.imara_band, memory.imara_label = "D", "At Risk"
        else:
            memory.imara_band, memory.imara_label = "E", "Distressed"

        # Breakdown with re-normalised (effective) weights for transparency
        memory.imara_components = [
            {
                "label": label,
                "value": int(round(max(0, min(100, value)))),
                "weight": round(weight / total_weight, 3),
            }
            for (label, value, weight) in active
        ]

    # ── Phase 5 ──────────────────────────────────────────────────

    def _generate_report(
        self, business_data: dict, memory: SharedMemory, synthesis: dict
    ) -> dict:
        """Generate the full structured report dict."""

        # ── Serialise all findings (full fields) ──
        def _serialise(f: AgentFinding) -> dict:
            return {
                "agent": f.agent,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "detail": f.detail,
                "financial_impact": f.financial_impact,
                "recommendation": f.recommendation,
                "roi_estimate": f.roi_estimate,
                "cost_of_inaction": f.cost_of_inaction,
                "benchmark_reference": f.benchmark_reference,
                "data_source": f.data_source,
                "quick_win": f.quick_win,
            }

        all_findings_serial = [_serialise(f) for f in memory.findings]

        # Group by agent
        by_agent: dict[str, list] = {}
        for f in memory.findings:
            by_agent.setdefault(f.agent, []).append(_serialise(f))

        # Sort each agent's findings: critical → high → medium → low
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for agent_findings in by_agent.values():
            agent_findings.sort(key=lambda f: sev_order.get(f["severity"], 9))

        # Quick wins
        quick_wins = [_serialise(f) for f in memory.get_quick_wins()]

        # Critical and high findings ranked by severity
        ranked = sorted(
            all_findings_serial,
            key=lambda f: (sev_order.get(f["severity"], 9), f["agent"])
        )

        # Generate narrative sections
        executive_summary = self._generate_executive_summary(memory, synthesis)
        roadmap = self._generate_roadmap(memory, synthesis)
        digital_twin = self._generate_digital_twin(memory)

        # Pull synthesis sections
        top_issues = synthesis.get("top_priority_issues", [])
        systemic_themes = synthesis.get("systemic_themes", [])
        situation = synthesis.get("situation", "")
        complication = synthesis.get("complication", "")
        resolution = synthesis.get("resolution", "")

        return {
            # Identity
            "business_name": memory.business_name,
            "industry": memory.industry or memory.industry_key,
            "industry_key": memory.industry_key,
            "currency": memory.currency,
            "annual_revenue": memory.annual_revenue,
            "headcount": memory.headcount,
            "country": memory.country,

            # Scores
            "scores": {
                "business_health": memory.business_health_score,
                "profitability": memory.profitability_score,
                "efficiency": memory.efficiency_score,
                "risk": memory.risk_score,
            },

            # Imara Score™ (branded composite hero metric)
            "imara_score": memory.imara_score,
            "imara_band": memory.imara_band,
            "imara_label": memory.imara_label,
            "imara_components": memory.imara_components,

            # Narrative (McKinsey SCR)
            "situation": situation,
            "complication": complication,
            "resolution": resolution,
            "executive_summary": executive_summary,

            # Findings
            "total_findings": len(memory.findings),
            "critical_findings": sum(1 for f in memory.findings if f.severity == "critical"),
            "high_findings": sum(1 for f in memory.findings if f.severity == "high"),
            "medium_findings": sum(1 for f in memory.findings if f.severity == "medium"),
            "low_findings": sum(1 for f in memory.findings if f.severity == "low"),

            "top_priority_issues": top_issues,
            "systemic_themes": systemic_themes,
            "quick_wins": quick_wins,
            "quick_wins_narrative": synthesis.get("quick_wins_narrative", ""),
            "strategic_plays_narrative": synthesis.get("strategic_plays_narrative", ""),
            "department_findings": by_agent,
            "all_findings_ranked": ranked[:20],  # Top 20 for dashboard

            # Roadmap and twin
            "implementation_roadmap": roadmap,
            "digital_twin_parameters": digital_twin,

            # Business structure
            "revenue_streams": memory.revenue_streams,
            "cost_centers": memory.cost_centers,
            "business_model_summary": memory.business_model_summary,
            "key_risks": memory.key_risks,
            "key_opportunities": memory.key_opportunities,

            # ── New agent outputs ─────────────────────────────────
            # Fraud & Anomaly Detection
            "fraud_risk_level": memory.fraud_risk_level,
            "fraud_risk_score": memory.fraud_risk_score,
            "fraud_indicators": memory.fraud_indicators,

            # Credit Readiness
            "credit_score": memory.credit_score,
            "credit_grade": memory.credit_grade,
            "credit_barriers": memory.credit_barriers,
            "credit_strengths": memory.credit_strengths,
            "credit_products": memory.credit_products,

            # Valuation
            "valuation_low": memory.valuation_low,
            "valuation_mid": memory.valuation_mid,
            "valuation_high": memory.valuation_high,
            "valuation_method": memory.valuation_method,
            "valuation_ebitda_multiple": memory.valuation_ebitda_multiple,
            "valuation_normalised_ebitda": memory.valuation_normalised_ebitda,

            # Forecast & Scenario
            "forecast_base_12m": memory.forecast_base_12m,
            "forecast_bull_12m": memory.forecast_bull_12m,
            "forecast_bear_12m": memory.forecast_bear_12m,
            "forecast_assumptions": memory.forecast_assumptions,
            "forecast_monthly": memory.forecast_monthly,

            # Market Intelligence
            "market_visibility_score": memory.market_visibility_score,
            "market_sentiment": memory.market_sentiment,
            "market_news": memory.market_news,
            "market_competitors": memory.market_competitors,
            "market_opportunities": memory.market_opportunities,
            "market_risks": memory.market_risks,
            "market_context_summary": memory.market_context_summary,
            "market_search_performed": memory.market_search_performed,
            "market_total_results": memory.market_total_results,

            # SA Tax Agent
            "sa_tax_risk_score": memory.sa_tax_risk_score,
            "sa_tax_summary": memory.sa_tax_summary,
            "sa_vat_status": memory.sa_vat_status,
            "sa_tax_clearance_status": memory.sa_tax_clearance_status,
            "sa_tax_performed": memory.sa_tax_performed,

            # SA Legal Agent
            "sa_legal_risk_score": memory.sa_legal_risk_score,
            "sa_legal_summary": memory.sa_legal_summary,
            "sa_bbbee_analysis": memory.sa_bbbee_analysis,
            "sa_cipc_status": memory.sa_cipc_status,
            "sa_legal_performed": memory.sa_legal_performed,

            # SA intake profile
            "entity_type": memory.entity_type,
            "bbbee_level": memory.bbbee_level,
            "report_audience": memory.report_audience,

            # Legacy compat
            "summary": executive_summary,
        }

    def _generate_executive_summary(self, memory: SharedMemory, synthesis: dict) -> str:
        cur = memory.currency
        rev = memory.annual_revenue
        concern_line = (
            f"\nThe client's stated primary concern was: \"{memory.primary_concern}\"\n"
            "Paragraph 1 must open by addressing this directly — either confirming it with data, "
            "reframing it with the actual root cause found, or expanding on it.\n"
            if memory.primary_concern else ""
        )
        prompt = f"""
Write a 4-paragraph McKinsey-quality executive summary for a forensic business analysis report.
{concern_line}

Client: {memory.business_name}
Industry: {memory.industry}
Annual Revenue: {cur} {rev:,.0f}
Health Score: {memory.business_health_score}/100
Findings: {len(memory.findings)} total | {sum(1 for f in memory.findings if f.severity == "critical")} critical | {sum(1 for f in memory.findings if f.severity == "high")} high

Situation: {synthesis.get("situation", "")}
Complication: {synthesis.get("complication", "")}
Resolution: {synthesis.get("resolution", "")}

Top priority issues:
{json.dumps(synthesis.get("top_priority_issues", [])[:3], indent=2)}

Paragraph structure:
1. SITUATION: Who is this business and what is its current strategic position?
2. FINDINGS: What are the 3 most material findings and their combined financial impact in {cur}?
3. IMPLICATIONS: What does inaction cost? What is the compounding risk over 12 months?
4. RECOMMENDATION: What is the single most important thing management must do in the next 30 days?

Rules:
- Every paragraph must contain at least one specific number anchored to the data
- No filler phrases ("It is important to...", "In order to...", "This report aims to...")
- Write in third-person, present tense
- Maximum 300 words total
- Professional but direct — a CEO should read this in 2 minutes and know exactly what to do
"""
        return self._call_claude(prompt)

    def _generate_roadmap(self, memory: SharedMemory, synthesis: dict) -> list:
        cur = memory.currency
        quick_wins = [f for f in memory.findings if f.quick_win]
        strategic = [f for f in memory.findings if not f.quick_win and f.severity in ("critical", "high")]

        prompt = f"""
Create a precise 90-day implementation roadmap for {memory.business_name}.
Currency: {cur}

QUICK WINS (action in < 30 days):
{chr(10).join(f"- {f.title}: {f.recommendation}" for f in quick_wins[:8])}

CRITICAL/HIGH PRIORITY (require planning):
{chr(10).join(f"- {f.title}: {f.recommendation}" for f in strategic[:8])}

Synthesis insights:
{synthesis.get("quick_wins_narrative", "")}
{synthesis.get("strategic_plays_narrative", "")}

Your PRIMARY CONCERN from client: {memory.primary_concern if memory.primary_concern else "Not specified"}

REQUIRED OUTPUT — a JSON array of exactly 3 phase objects:
[
  {{
    "phase": "Phase 1: Immediate Actions",
    "priority_level": "critical",
    "focus": "1 sentence: what this phase targets",
    "actions": [
      {{"action": "Specific action statement", "owner": "Department/Role", "impact": "$ or % outcome"}}
    ],
    "expected_impact": "Combined expected outcome in {cur} or %"
  }},
  {{
    "phase": "Phase 2: 30–60 Day Programme",
    "priority_level": "high",
    "focus": "1 sentence",
    "actions": [...],
    "expected_impact": "..."
  }},
  {{
    "phase": "Phase 3: 60–90 Day Strategic",
    "priority_level": "medium",
    "focus": "1 sentence",
    "actions": [...],
    "expected_impact": "..."
  }}
]

Rules:
- Each phase must have 4–7 specific actions
- Every action must name an owner and a measurable impact
- Actions must be specific to {memory.business_name}'s actual findings — not generic advice
- Quick wins MUST appear in Phase 1
- Return ONLY the JSON array — no markdown, no explanation
"""
        raw = self._call_claude(prompt)
        raw = _strip_json(raw)
        try:
            roadmap = json.loads(raw)
            if not isinstance(roadmap, list):
                roadmap = [roadmap]
            return roadmap
        except Exception:
            return []

    def _generate_digital_twin(self, memory: SharedMemory) -> dict:
        """
        Extract key financial parameters for the What-If digital twin simulator.
        Returns a simple dict consumed by the /api/simulate endpoint.
        """
        rev = memory.annual_revenue
        return {
            "base_revenue": rev,
            "headcount": memory.headcount,
            "currency": memory.currency,
            "industry_key": memory.industry_key,
            "credit_score": memory.credit_score,
            "valuation_mid": memory.valuation_mid,
            "forecast_base_12m": memory.forecast_base_12m,
        }


def _strip_json(text: str) -> str:
    """Strip markdown code fences from a Claude JSON response."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()
