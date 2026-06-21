"""Tests for the prose verifier (Tier 1.1) - qualitative narrative vs computed ratio status."""
from memory.shared_memory import AgentFinding
from services.prose_verifier import verify_prose


def _f(title, detail, **kw):
    return AgentFinding(
        agent=kw.get("agent", "FinancialAgent"),
        category=kw.get("category", "Liquidity"),
        severity=kw.get("severity", "medium"),
        title=title,
        detail=detail,
        financial_impact=kw.get("financial_impact", "R0"),
        recommendation=kw.get("recommendation", "-"),
        roi_estimate=kw.get("roi_estimate", "-"),
        benchmark_reference=kw.get("benchmark_reference", ""),
    )


RATIOS = {
    "current_ratio": {"label": "Current ratio", "value": 0.4, "unit": "x", "status": "critical"},
    "gross_margin":  {"label": "Gross margin", "value": 42.0, "unit": "%", "status": "good"},
    "debtor_days":   {"label": "Debtor days", "value": 55, "unit": "days", "status": "warning"},
}


def test_positive_word_vs_critical_is_flagged():
    f = _f("Liquidity", "The business maintains a comfortable current ratio overall.")
    s = verify_prose([f], RATIOS)
    assert f.prose_check == "conflict"
    assert "current ratio" in f.prose_note.lower()
    assert s["flagged"] == 1


def test_negative_word_vs_good_is_flagged():
    f = _f("Margins", "Gross margin remains weak versus sector peers.")
    s = verify_prose([f], RATIOS)
    assert f.prose_check == "conflict"
    assert s["flagged"] == 1


def test_positive_word_vs_good_is_consistent_not_flagged():
    f = _f("Margins", "Gross margin is strong and healthy.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_negative_word_vs_critical_is_consistent_not_flagged():
    f = _f("Liquidity", "The current ratio is weak and strained.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_warning_status_is_never_flagged():
    f = _f("Debtors", "Debtor days look concerning and poor.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_negation_suppresses_flag():
    f = _f("Liquidity", "The current ratio is not comfortable at all.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_no_metric_phrase_not_flagged():
    f = _f("Brand", "The leadership team is strong and the brand is healthy.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_missing_status_or_value_is_safe():
    ratios = {"current_ratio": {"label": "Current ratio", "value": None, "status": "critical"},
              "gross_margin": {"label": "Gross margin", "value": 42.0}}  # no status
    f1 = _f("A", "comfortable current ratio")
    f2 = _f("B", "weak gross margin")
    s = verify_prose([f1, f2], ratios)
    assert f1.prose_check == "" and f2.prose_check == ""
    assert s["flagged"] == 0


def test_empty_inputs_are_safe():
    assert verify_prose([], {}) == {"checked": 0, "flagged": 0, "flag_titles": []}
    assert verify_prose([], None)["flagged"] == 0


def test_at_most_one_flag_per_finding():
    f = _f("Both", "A comfortable current ratio and a weak gross margin in one breath.")
    s = verify_prose([f], RATIOS)
    # one finding -> counted once even though two metrics could conflict
    assert s["flagged"] == 1
    assert f.prose_check == "conflict"


# ---- pressure-test regressions (grammatical adjacency, added after probing) ----
def test_health_word_about_different_subject_is_not_flagged():
    # "strong" modifies the leadership team, NOT the current ratio -> must NOT flag
    f = _f("x", "The company has a strong leadership team and a current ratio of 0.4x.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_health_word_across_clause_boundary_is_not_flagged():
    f = _f("x", "Margins are strong; separately the current ratio sits at 0.4.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""


def test_post_copula_with_decimal_is_flagged():
    # decimals (0.4x) must not be mistaken for a clause boundary
    f = _f("x", "The current ratio of 0.4x is comfortable.")
    verify_prose([f], RATIOS)
    assert f.prose_check == "conflict"


def test_negation_after_copula_suppresses():
    f = _f("x", "The current ratio is not comfortable.")
    verify_prose([f], RATIOS)
    assert f.prose_check == ""
