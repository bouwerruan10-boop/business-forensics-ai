"""Regression tests for crashes found by the 2026-06-29 adversarial fuzz pass.

Each test pins a specific hostile/corrupted-record shape that previously raised, proving
the export/ledger/score surfaces now degrade safely. These shapes don't come from the live
pipeline (every value is computed deterministically) — they model a corrupted/old-schema DB
record, which is exactly what report_safety.normalize_report defends against.
"""
from services.report_safety import normalize_report, _as_number
from services.report_generator import generate_pdf_report
from services.html_report import generate_html_report
from services.reason_codes import reason_codes
from services.score_disclosure import build_disclosure
from services.claim_ledger import build_claim_ledger

INJECT = "<script>alert(1)</script>"
HUGE = 10 ** 18


# ── report_safety.normalize_report ───────────────────────────────────────────

def test_as_number_coerces_and_rejects():
    assert _as_number("58") == 58.0
    assert _as_number("1,234.5") == 1234.5
    assert _as_number(42) == 42
    for junk in ("bad", None, [], {}, True, float("inf"), float("nan")):
        assert _as_number(junk) is None


def test_normalize_drops_non_numeric_scalars():
    r = normalize_report({"imara_score": "bad", "credit_score": "x", "valuation_mid": "12,000"})
    assert "imara_score" not in r and "credit_score" not in r   # junk dropped -> renderer default
    assert r["valuation_mid"] == 12000.0                         # numeric string coerced


def test_normalize_filters_non_dict_list_elements():
    r = normalize_report({"imara_components": [None, 1, "x", {"label": "Profitability"}]})
    assert r["imara_components"] == [{"label": "Profitability"}]


def test_normalize_coerces_component_value_weight_without_mutating_caller():
    src = {"imara_components": [{"label": "P", "value": "bad", "weight": "x"},
                               {"label": "Q", "value": float("inf"), "weight": HUGE}]}
    r = normalize_report(src)
    c0, c1 = r["imara_components"]
    assert "value" not in c0 and "weight" not in c0     # junk strings dropped
    assert "value" not in c1 and c1["weight"] == HUGE   # inf dropped, finite kept
    # caller's original dicts must be untouched (shallow-copy aliasing guard)
    assert src["imara_components"][0]["value"] == "bad"


def test_normalize_sanitizes_nested_ratio_values():
    r = normalize_report({"financial_ratios": {"net_margin": {"value": "bad", "benchmark": [], "label": "NM"},
                                               "gm": {"value": "33.2"}}})
    assert "value" not in r["financial_ratios"]["net_margin"]
    assert "benchmark" not in r["financial_ratios"]["net_margin"]
    assert r["financial_ratios"]["net_margin"]["label"] == "NM"   # other keys preserved
    assert r["financial_ratios"]["gm"]["value"] == 33.2


# ── score surfaces (called on the RAW report in production) ───────────────────

def test_reason_codes_safe_on_string_value_weight():
    rc = reason_codes({"imara_score": 50, "imara_components": [
        {"label": "Profitability", "value": "bad", "weight": "x"},
        {"label": "Credit Readiness", "value": 40, "weight": 0.5}]})
    assert isinstance(rc, dict)   # no ValueError on float("x")


def test_build_disclosure_safe_on_hostile_components():
    d = build_disclosure({"imara_score": 50, "imara_band": "B", "imara_components": [
        {"label": INJECT, "value": float("inf"), "weight": HUGE},
        {"label": "Profitability", "value": 40, "weight": 0.5}]})
    assert isinstance(d, dict) and d.get("available") is True


# ── claim_ledger / narrative figure verification (overflow guard) ────────────

def test_claim_ledger_safe_on_overflow_amount():
    # a 400-digit rand figure parses to float('inf') -> round() previously overflowed
    rep = {"financial_ratios": {}, "financial_figures": {},
           "department_findings": {"Fin": [{"title": "X", "detail": "R" + "9" * 400}]}}
    led = build_claim_ledger(rep)
    assert isinstance(led, dict)


def test_assembly_services_survive_nonfinite_figures():
    """Regression for the round(inf)/int(inf) bug CLASS: services that round() arithmetic on
    financial_figures must not OverflowError when figures carry inf/NaN (a corrupted/adversarial
    document can produce them). Caught macro_data's annual_revenue-fallback inf-leak."""
    import json as _json
    INF, NAN = float("inf"), float("nan")
    figs = {"revenue": INF, "operating_profit": NAN, "total_debt": INF, "equity": 0, "interest": INF,
            "net_profit": -INF, "ebitda": INF, "current_assets": INF, "current_liabilities": NAN,
            "payables": INF, "inventory": INF, "accounts_receivable": INF, "gross_profit": INF}
    rep = {"financial_figures": figs, "annual_revenue": INF, "industry_key": "retail",
           "imara_score": INF, "imara_band": "B", "currency": "ZAR"}
    from services.macro_data import firm_macro_sensitivity
    from services.lender_view import run_lender_view
    from services.affordability import assess_affordability
    from services.credit_memo import build_credit_memo
    from services.working_capital import build_working_capital
    from services.distress_score import altman_z_em
    # must not raise (a crash here = the analysis fails end-to-end)
    cases = {
        "macro": firm_macro_sensitivity(rep),
        "lender_view": run_lender_view(figs, {}, {}, INF),
        "affordability": assess_affordability(figs, {"adjusted_ebitda_low": INF}),
        "credit_memo": build_credit_memo(rep),
        "working_capital": build_working_capital(rep),
        "distress": altman_z_em(figs, "B"),
    }
    for name, out in cases.items():
        assert isinstance(out, dict), name
    _json.dumps(cases["macro"], allow_nan=False)   # the fixed path is strict-JSON safe


def test_narrative_currency_overflow_safe():
    # the _currency_claims twin of the overflow guard: a huge amount in NARRATIVE prose
    # (not a finding) previously crashed verify_narrative -> the whole pipeline (caught by
    # the full-pipeline pressure test). Pin it at the unit level too.
    from services.narrative_claims import verify_narrative
    rep = {"executive_summary": "An upside of R" + "9" * 400 + " exists.",
           "financial_ratios": {}, "financial_figures": {}}
    assert isinstance(verify_narrative(rep), dict)


# ── exporters: corrupted claim_ledger sub-shapes ─────────────────────────────

_BASE = {"business_name": "Acme", "industry": "retail", "currency": "ZAR", "imara_score": 58,
         "imara_band": "B", "imara_components": [], "department_findings": {}, "all_findings_ranked": [],
         "financial_ratios": {}, "scores": {}, "implementation_roadmap": []}


def test_exporters_safe_on_corrupted_ledger_subfields():
    bad = {**_BASE, "claim_ledger": {"available": True, "overall": INJECT, "assurance": "not-a-dict",
                                     "narrative_claims": "not-a-list", "finding_figure_claims": "x"}}
    assert generate_pdf_report(dict(bad), audience="banker")[:4] == b"%PDF"
    h = generate_html_report(dict(bad))
    assert isinstance(h, str) and INJECT not in h   # injection escaped, no crash


def test_exporters_safe_on_hostile_components_and_scalars():
    bad = {**_BASE, "imara_score": "bad", "credit_score": "x",
           "imara_components": [None, 1, {"label": INJECT, "value": "bad", "weight": "x"}],
           "financial_ratios": {"net_margin": {"value": "bad", "benchmark": []}}}
    assert generate_pdf_report(dict(bad), audience="owner")[:4] == b"%PDF"
    assert isinstance(generate_html_report(dict(bad)), str)
