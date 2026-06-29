"""Invariant locks for two structural guarantees the dossier flagged (H4, D3).

These pin properties a future refactor could silently break:
  H4 — the Imara Score must stay business-level (no owner / personal-credit term).
  D3 — every governance/explainability surface must carry the decision-support shield.
"""
from services.score_disclosure import _ALL_COMPONENTS
from services.governance import decision_support_notice
from services.reason_codes import reason_codes
from services.model_card import model_card
from services.ahp import PRODUCTION_WEIGHTS

_FORBIDDEN = ("owner", "personal", "director", "individual", "consumer", "bbbee", "b-bbee", "race")

_EXPECTED_COMPONENTS = {
    "Profitability", "Credit Readiness", "Risk & Compliance", "Operational Efficiency",
    "Financial Integrity", "Market Visibility", "Tax Compliance", "Legal Compliance",
}


def test_score_components_are_business_level_only():
    # H4: no Imara Score component may be an owner / personal-credit proxy.
    for label in _ALL_COMPONENTS:
        low = label.lower()
        assert not any(term in low for term in _FORBIDDEN), "owner/personal term in component: " + label
    assert set(_ALL_COMPONENTS) == _EXPECTED_COMPONENTS   # locks the exact business-level set


def test_production_weights_are_business_level_only():
    for label in PRODUCTION_WEIGHTS:
        low = str(label).lower()
        assert not any(term in low for term in _FORBIDDEN), "owner/personal term in weights: " + label


def test_decision_support_shield_is_intact():
    # D3: the shield must keep its NCA + not-a-credit-decision framing.
    d = decision_support_notice()
    blob = " ".join(str(v) for v in d.values()).lower()
    assert "national credit act" in blob
    assert "decision" in d.get("is_not", "").lower()


def test_explainability_surfaces_carry_a_disclaimer():
    # D3: reason codes + model card must each carry the decision-support framing.
    rep = {"imara_score": 60, "imara_band": "B",
           "imara_components": [{"label": "Profitability", "weight": 0.3, "value": 50},
                                {"label": "Credit Readiness", "weight": 0.3, "value": 40}]}
    rc = reason_codes(rep)
    assert "disclaimer" in rc and "credit decision" in rc["disclaimer"].lower()
    card = model_card()
    assert "governance" in card and "intended_use" in card
