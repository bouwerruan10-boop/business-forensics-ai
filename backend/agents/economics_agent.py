"""
EconomicsAgent — reads the SA macro environment and translates it into effects
on ONE firm's internal economy. Deterministic-first: the firm's macro exposure
is computed by `firm_macro_sensitivity` from its own statements; the LLM only
narrates the implications and cites the provided (dated) indicators. Runs in the
concurrent pre-synthesis tail; writes disjoint `macro_*` fields. The score-based
macro stress test is computed on-demand (GET /api/report/{id}/macro), since the
Imara Score isn't finalised until after this phase.
"""
from agents.base_agent import BaseAgent
from agents.specialist_agents import FINDING_RULES
from memory.shared_memory import SharedMemory, AgentFinding
from services.macro_data import firm_macro_sensitivity, macro_summary_text, SA_MACRO


class EconomicsAgent(BaseAgent):
    name = "Economic Environment Agent"
    system_prompt = (
        "You are a South African macro-economist advising an SME. You translate the macro environment "
        "(SARB repo rate, inflation, GDP growth, the rand, electricity tariffs, unemployment) into concrete, "
        "quantified effects on THIS business's cash flow, costs, debt servicing and resilience.\n"
        "Rules: cite ONLY the dated indicators provided to you — never invent macro figures. Tie every point to the "
        "firm's own numbers (the computed macro-exposure profile gives you the ZAR sensitivities). Be specific about "
        "which macro factor hurts this firm most and what to do (fix/hedge interest rates, energy efficiency / solar, "
        "FX hedging or local sourcing, pricing/pass-through, building a buffer)."
    ) + "\n" + FINDING_RULES

    def analyze(self, business_data: dict, memory: SharedMemory) -> list[AgentFinding]:
        # Mini-report from what's available at this phase (figures set in Phase 1c).
        mini = {
            "industry_key": memory.industry_key or "general",
            "annual_revenue": memory.annual_revenue,
            "financial_figures": memory.financial_figures or {},
            "financial_fundamentals_score": memory.financial_fundamentals_score,
        }
        # 1) Deterministic exposure profile — always set, even if the LLM call fails.
        try:
            sens = firm_macro_sensitivity(mini)
            memory.macro_sensitivity = sens
            memory.macro_overall_exposure = sens.get("overall_exposure", "")
            memory.macro_top_driver = sens.get("top_driver", "")
        except Exception as exc:
            print("[economics] sensitivity failed: {}".format(exc))
            sens = {}

        memory.macro_performed = True
        memory.macro_summary = "Macro exposure: {} (top driver: {}). As of {}.".format(
            memory.macro_overall_exposure or "n/a", memory.macro_top_driver or "n/a", SA_MACRO["as_of"])

        # 2) LLM narrative findings, grounded in the snapshot + the firm's sensitivities.
        try:
            grounding = macro_summary_text(mini)
        except Exception:
            grounding = ""
        prompt = f"""
{grounding}

BUSINESS CONTEXT:
{memory.to_context_summary()}

TASK — Assess how the South African macro-economic environment affects THIS firm's internal economy.
For each material exposure (interest rates, inflation/input costs, electricity tariffs, the rand):
- State the effect on this firm in ZAR, using the macro-exposure figures above (do not invent macro numbers).
- Note how it flows to cash flow, margins, debt serviceability or resilience.
- Give a specific, actionable mitigation.
Prioritise the firm's biggest exposure ({memory.macro_top_driver or 'see profile'}). Flag if a plausible adverse
macro scenario (higher rates + weaker rand + tariff hikes) would push the business into a loss.
"""
        try:
            raw = self._call_claude(prompt)
            findings = self._parse_findings(raw, memory)
        except Exception as exc:
            print("[economics] narrative failed, deterministic fields kept: {}".format(exc))
            findings = []
        return findings
