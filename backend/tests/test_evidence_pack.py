"""Pilot evidence-pack tests (conceptual soundness + Z'' convergence + honest status)."""
from services.evidence_pack import build_evidence_pack

_REPORT = {
    "imara_score": 62, "imara_band": "B", "imara_label": "Bankable",
    "imara_confidence": "high", "imara_completeness": 88,
    "imara_components": [
        {"label": "Profitability", "value": 55, "weight": 0.30},
        {"label": "Credit Readiness", "value": 70, "weight": 0.25},
    ],
    "distress_score": {"available": True, "zone": "grey",
                       "convergence": {"agreement": "partial", "statement": "Z'' grey vs band B — consistent."}},
}


def test_pack_has_four_pillars_with_honest_status():
    p = build_evidence_pack(_REPORT)
    assert p["available"] is True
    statuses = {x["pillar"]: x["status"] for x in p["minimum_viable_evidence"]}
    assert statuses["Conceptual soundness"] == "documented"
    assert statuses["Benchmark convergence"] == "available"      # Z'' convergence present
    assert statuses["Expert-panel agreement"] == "pending"
    assert statuses["Outcome validation"] == "not_started_cold_start"   # honest cold-start


def test_pack_states_outcome_targets_not_validated():
    p = build_evidence_pack(_REPORT)
    t = p["outcome_validation_roadmap"]["targets"]
    assert t["gini_min"] == 0.40 and t["auc_min"] == 0.70 and t["ks_min"] == 0.25
    # never claims validated
    assert "not" in p["disclaimer"].lower()
    assert "validated" in p["headline"].lower()    # explicitly says NOT a validated predictor


def test_pack_convergence_pending_without_zscore():
    rep = dict(_REPORT)
    rep["distress_score"] = {}      # no convergence
    p = build_evidence_pack(rep)
    bench = {x["pillar"]: x["status"] for x in p["minimum_viable_evidence"]}["Benchmark convergence"]
    assert bench == "pending"


def test_pack_includes_model_card_and_logic():
    p = build_evidence_pack(_REPORT)
    assert p["model_card"] and p["model_logic"]


def test_pack_robust():
    assert build_evidence_pack("x")["available"] is False
    assert build_evidence_pack({})["available"] is False
    assert build_evidence_pack({"imara_score": 50})["available"] is False
