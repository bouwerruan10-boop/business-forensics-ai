"""Claim/Evidence contract tests: uniform claim, narrative number verification, ledger."""
from fastapi.testclient import TestClient

from services.claim_contract import make_claim, verify_metric, verify_currency, grade_confidence
from services.narrative_claims import verify_narrative, verify_finding_figures
from services.claim_ledger import build_claim_ledger, record_claim_ledger, _assurance


# ---- claim_contract ----

def test_verify_metric_conflict_verified_unverified():
    assert verify_metric(21.3, 33.2, "%", "gross margin")[0] == "conflict"
    assert verify_metric(33.0, 33.2, "%", "gross margin")[0] == "verified"   # within tolerance
    assert verify_metric(50, None, "days")[0] == "unverified"


def test_verify_currency_matches_known_figure():
    status, _, src = verify_currency(450_000, {"net_profit": 450_000, "revenue": 5_000_000})
    assert status == "verified" and src == "net_profit"
    assert verify_currency(1_200_000, {"revenue": 5_000_000})[0] == "unverified"


def test_make_claim_normalises():
    c = make_claim("x", "bogus_kind", value=1, verification="nonsense")
    assert c["kind"] == "qualitative"           # unknown kind -> qualitative
    assert c["verification"] == "unverified"    # unknown status -> unverified


# ---- Phase 3: calibrated per-claim confidence ----

def test_grade_confidence_bands():
    # verified, near-exact -> high; loose-but-verified -> still reasonable
    assert grade_confidence("verified", 33.2, 33.2, "%") == (0.97, "high")
    assert grade_confidence("verified", 35.0, 33.2, "%")[1] in ("high", "medium")
    assert grade_confidence("verified")[1] == "high"          # status-only default
    # conflict -> low (we are confident the claim is wrong); unverified estimate -> low
    assert grade_confidence("conflict")[1] == "low"
    assert grade_confidence("unverified")[1] == "low"
    # hostile numbers never crash
    assert grade_confidence("verified", "x", None, "%")[1] == "high"


def test_make_claim_attaches_confidence_and_clamps():
    c = make_claim("m", "metric", value=33.2, verification="verified", computed=33.2, unit="%")
    assert c["confidence"] == 0.97 and c["confidence_band"] == "high"
    # explicit confidence overrides and clamps to [0,1]
    assert make_claim("x", "metric", confidence=5)["confidence"] == 1.0
    assert make_claim("x", "metric", confidence="bad")["confidence"] == 0.0


def test_narrative_claims_carry_confidence():
    r = verify_narrative(_REPORT)
    assert all("confidence" in c and "confidence_band" in c for c in r["claims"])
    # the conflicting metric must be low-confidence; a verified one high
    conf = next(c for c in r["claims"] if c["verification"] == "conflict")
    assert conf["confidence_band"] == "low"
    ver = next(c for c in r["claims"] if c["verification"] == "verified")
    assert ver["confidence_band"] == "high"


# ---- narrative_claims ----

_REPORT = {
    "financial_ratios": {"gross_margin": {"value": 33.2, "label": "gross margin"},
                         "debtor_days": {"value": 52, "label": "debtor days"}},
    "financial_figures": {"revenue": 5_000_000, "net_profit": 450_000},
    "annual_revenue": 5_000_000,
    "executive_summary": ("The business runs a gross margin of 21.3% and debtor days of 52. "
                          "Net profit was R450,000 and there is a R1.2 million working-capital opportunity."),
    "systemic_themes": [{"title": "Working capital", "narrative": "Material.", "combined_impact": "R1.2 million per year"}],
}


def test_narrative_flags_conflict_and_unverified():
    r = verify_narrative(_REPORT)
    assert r["available"] is True
    # the LLM's 21.3% margin conflicts with the computed 33.2%
    assert any(c["kind"] == "metric" and c["verification"] == "conflict" for c in r["claims"])
    # the debtor days and the R450,000 match computed values
    assert any(c["verification"] == "verified" for c in r["claims"])
    # the R1.2m opportunity is not traceable -> unverified, never a silent pass
    assert any(c["kind"] == "currency" and c["verification"] == "unverified" for c in r["claims"])


def test_narrative_robust_to_hostile():
    assert verify_narrative("x")["available"] is False
    assert verify_narrative(None)["summary"] == {}
    assert verify_narrative({})["summary"]["total"] == 0


# ---- Phase 2: roadmap + market/tax/legal summaries are now scanned ----

def test_phase2_roadmap_impacts_are_verified():
    rep = {
        "financial_ratios": {"gross_margin": {"value": 33.2, "label": "gross margin"}},
        "financial_figures": {"net_profit": 450_000},
        "implementation_roadmap": [
            {"phase": "Phase 1", "focus": "Stop the bleed", "expected_impact": "Recover R450,000",
             "actions": [{"action": "Lift gross margin to 21.3% by repricing", "owner": "Finance",
                          "impact": "R900,000 uplift"}]},
        ],
    }
    r = verify_narrative(rep)
    secs = {c["section"] for c in r["claims"]}
    assert any(s.startswith("Roadmap:") for s in secs)
    # R450,000 traces to computed net_profit -> verified
    assert any(c["kind"] == "currency" and c["verification"] == "verified" for c in r["claims"])
    # the 21.3% margin in the action conflicts with computed 33.2%
    assert any(c["kind"] == "metric" and c["verification"] == "conflict" for c in r["claims"])
    # the R900,000 projection is not traceable -> honest unverified, never a silent pass
    assert any(c["kind"] == "currency" and c["verification"] == "unverified" for c in r["claims"])


def test_phase2_finding_figures_verified_and_unverified():
    rep = {
        "financial_figures": {"net_profit": 450_000},
        "department_findings": {
            "FinancialAgent": [
                {"title": "Cash drain", "financial_impact": "R450,000 annual cash drain",
                 "recommendation": "Recover R450,000 by tightening terms",
                 "roi_estimate": "3x return", "cost_of_inaction": "Up to R2,000,000 lost over 3 years"},
            ],
        },
    }
    r = verify_finding_figures(rep)
    assert r["available"] is True
    # R450,000 traces to computed net_profit -> verified
    assert any(c["verification"] == "verified" and c["value"] == 450_000 for c in r["claims"])
    # the R2,000,000 cost-of-inaction projection is not traceable -> honest unverified
    assert any(c["verification"] == "unverified" and c["value"] == 2_000_000 for c in r["claims"])
    assert r["summary"]["verified"] >= 1 and r["summary"]["unverified"] >= 1


def test_finding_detail_currency_covered_and_deduped():
    # currency in a finding's `detail` prose is now checked (faithfulness only did metrics there);
    # and the same amount across detail + financial_impact dedups to ONE claim per finding.
    rep = {
        "financial_figures": {"net_profit": 450_000},
        "department_findings": {"Fin": [
            {"title": "Drain", "detail": "A hidden R5,000,000 exposure sits in the detail prose.",
             "financial_impact": "R450,000 drain", "recommendation": "Fix the R450,000 leak"},
        ]},
    }
    r = verify_finding_figures(rep)
    vals = [c["value"] for c in r["claims"]]
    assert 5_000_000 in vals                       # detail currency now scanned
    assert vals.count(450_000) == 1                # detail+impact+rec dedup to one per finding
    assert any(c["verification"] == "verified" and c["value"] == 450_000 for c in r["claims"])
    assert any(c["verification"] == "unverified" and c["value"] == 5_000_000 for c in r["claims"])


def test_phase2_finding_figures_robust_to_hostile():
    assert verify_finding_figures("x")["available"] is False
    assert verify_finding_figures(None)["summary"] == {}
    # hostile shapes: non-dict findings, None fields, wrong types -> never crash
    for bad in (
        {"department_findings": "not-a-dict"},
        {"department_findings": {"A": [None, 42, {"financial_impact": None}]}},
        {"all_findings_ranked": [{"recommendation": 123, "cost_of_inaction": ["x"]}]},
    ):
        out = verify_finding_figures(bad)
        assert out["available"] is True and isinstance(out["claims"], list)


def test_phase2_ledger_folds_finding_figures():
    # an untraceable finding figure (no narrative) must flip overall to unverified_present
    rep = {"financial_ratios": {}, "financial_figures": {},
           "department_findings": {"A": [{"title": "X", "cost_of_inaction": "R2,500,000 at risk"}]}}
    led = build_claim_ledger(rep)
    assert led["finding_figures"]["checked"] >= 1
    assert led["finding_figures"]["unverified"] >= 1
    assert led["overall"] == "unverified_present"
    assert "finding figures traced" in led["headline"]


def test_phase2_sa_summaries_scanned():
    rep = {
        "financial_ratios": {},
        "financial_figures": {"vat_liability": 320_000},
        "sa_tax_summary": "Estimated VAT exposure is R320,000 for the period.",
        "market_context_summary": "An untapped segment worth R5 million was identified.",
    }
    r = verify_narrative(rep)
    secs = {c["section"] for c in r["claims"]}
    assert "SA tax summary" in secs and "Market intelligence" in secs
    # R320,000 traces to a computed figure; R5m market estimate does not
    assert any(c["verification"] == "verified" for c in r["claims"])
    assert any(c["verification"] == "unverified" for c in r["claims"])


# ---- claim_ledger ----

def test_ledger_overall_states():
    assert build_claim_ledger(_REPORT)["overall"] == "conflicts_present"
    clean = {"financial_ratios": {}, "financial_figures": {"revenue": 5_000_000},
             "executive_summary": "Revenue is R5,000,000."}
    assert build_claim_ledger(clean)["overall"] == "all_clear"
    est = {"financial_ratios": {}, "financial_figures": {}, "executive_summary": "An opportunity of R2 million exists."}
    assert build_claim_ledger(est)["overall"] == "unverified_present"


def test_ledger_folds_finding_signals():
    rep = dict(_REPORT)
    rep["faithfulness_summary"] = {"checked": 8, "confirmed": 7, "conflicts": 1, "benchmark_conflicts": 0}
    rep["finding_quality"] = {"strong": 5, "adequate": 3, "weak": 1}
    led = build_claim_ledger(rep)
    assert led["findings"]["checked"] == 8 and led["findings"]["conflicts"] == 1
    assert led["quality"]["weak"] == 1
    assert "verified against your computed data" in led["headline"]


def test_ledger_robust():
    assert build_claim_ledger("x")["available"] is False
    assert build_claim_ledger(None)["available"] is False


# ---- Phase 3b: assurance roll-up + fail-closed enforcement ----

def test_phase3_assurance_rollup():
    a = build_claim_ledger(_REPORT)["assurance"]
    assert a["total_claims"] >= 1
    assert a["verified"] + a["conflicts"] + a["unverified"] == a["total_claims"]
    assert 0 <= a["coverage_pct"] <= 100
    assert isinstance(a["avg_confidence"], float)
    assert a["contract_enforced"] is True       # verifier-produced claims carry the full contract
    assert "of" in a["statement"]


def test_phase3_assurance_detects_contract_leak():
    good = make_claim("ok", "currency", value=1000, verification="verified", computed=1000)
    leak = {"text": "rogue", "verification": "verified"}   # no confidence / no explanation
    a = _assurance([good, leak])
    assert a["contract_enforced"] is False and a["leaks"]


def test_phase3_fail_closed_forces_review(monkeypatch):
    # a leaked claim (missing confidence/explanation) must push the WHOLE report to needs-review
    import services.narrative_claims as nc

    def _leaky(_report):
        return {"available": True, "claims": [{"text": "rogue", "verification": "verified"}],
                "summary": {"total": 1, "verified": 1, "conflicts": 0, "unverified": 0}}

    monkeypatch.setattr(nc, "verify_narrative", _leaky)
    led = build_claim_ledger({"financial_ratios": {}, "financial_figures": {}})
    assert led["assurance"]["contract_enforced"] is False
    assert led["overall"] == "conflicts_present"     # fail-closed override


def test_phase3_assurance_robust():
    assert _assurance(None)["total_claims"] == 0
    assert _assurance([None, 42, "x"])["total_claims"] == 0   # non-dicts ignored
    assert _assurance([])["coverage_pct"] == 100.0            # vacuous: nothing unverified


def test_ledger_record_is_immutable(tmp_path, monkeypatch):
    import services.database as db
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "ledger.db")
    db.init_db()
    res = record_claim_ledger("a-cl", build_claim_ledger(_REPORT))
    assert res["recorded"] is True and res["record_hash"]
    rows = [r for r in db.get_audit("a-cl") if r.get("type") == "claim_ledger"]
    assert len(rows) == 1
    assert db.verify_audit_chain()["intact"] is True


# ---- endpoint + serialization ----

def test_endpoint_returns_ledger():
    import main
    main.analyses["t-claim-ledger"] = dict(_REPORT)
    try:
        client = TestClient(main.app)
        res = client.get("/api/report/t-claim-ledger/claim-ledger")
        assert res.status_code == 200
        assert res.json()["overall"] == "conflicts_present"
    finally:
        main.analyses.pop("t-claim-ledger", None)


def test_evidence_plain_language_now_serialised():
    # the finding serialiser must now include the (previously dropped) evidence field
    import agents.ceo_agent as ce
    import inspect
    src = inspect.getsource(ce.CEOAgent._generate_report)
    assert "evidence_plain_language" in src
