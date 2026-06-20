"""
Governance framing for the Imara Score — the standing, legally-careful statement of
what the Score IS and ISN'T. Surfaced in exports, the public Score contract, and the
model card. Addresses the SA NCA (no reckless lending; affordability assessment;
human-in-the-loop) and POPIA (transparency) context.
"""

DECISION_SUPPORT = {
    "classification": "decision-support analytics",
    "is_not": "a credit score, a creditworthiness determination, or a lending decision",
    "intended_use": ("Supports a registered credit provider's own NCA affordability assessment "
                     "and a human analyst's judgement. A person must make the final credit decision."),
    "nca": ("Not a substitute for the pre-agreement affordability assessment required by the "
            "National Credit Act (Act 34 of 2005, s78–81); does not authorise lending and must "
            "not be used to enable reckless credit (s80)."),
    "popia": ("Processes business and financial information provided by the client; figures are "
              "extracted deterministically and shown with their source (POPIA, Act 4 of 2013)."),
    "fairness": ("B-BBEE status and other transformation/ownership attributes are treated as "
                 "informational context only and never lower the Score."),
    "human_in_the_loop": True,
    "explainability": "Principal score factors are disclosed (reason codes); the scoring math is deterministic.",
}


def decision_support_notice() -> dict:
    return dict(DECISION_SUPPORT)
