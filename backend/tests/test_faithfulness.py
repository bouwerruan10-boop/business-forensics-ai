"""Faithfulness verifier — metric AND benchmark cross-checks (v1.76)."""
from services.faithfulness import verify_findings


class _F:
    def __init__(self, title, detail="", benchmark_reference=""):
        self.title = title
        self.detail = detail
        self.benchmark_reference = benchmark_reference


_RATIOS = {
    "gross_margin": {"value": 18.0, "benchmark": 33.2, "unit": "%", "label": "Gross Margin"},
    "debtor_days": {"value": 54.0, "benchmark": 35.0, "unit": "days", "label": "Debtor Days"},
    "current_ratio": {"value": 0.69, "benchmark": 1.5, "unit": "x", "label": "Current Ratio"},
}


# ── existing metric behaviour must still hold ──────────────────────────────────
def test_metric_value_confirmed():
    f = _F("GM", "Gross margin is 18% this year.")
    s = verify_findings([f], _RATIOS)
    assert f.verification == "confirmed"
    assert s["checked"] == 1 and s["confirmed"] == 1 and s["conflicts"] == 0


def test_metric_value_conflict():
    f = _F("GM", "Gross margin is a healthy 45%.")  # computed is 18%
    s = verify_findings([f], _RATIOS)
    assert f.verification == "conflict"
    assert s["conflicts"] == 1


# ── new benchmark cross-check ──────────────────────────────────────────────────
def test_benchmark_confirmed():
    f = _F("GM", "Gross margin 18% vs a sector benchmark of 33%.")
    s = verify_findings([f], _RATIOS)
    assert f.benchmark_verification == "confirmed"
    assert s["benchmark_checked"] == 1 and s["benchmark_confirmed"] == 1
    assert s["benchmark_conflicts"] == 0


def test_benchmark_conflict_flags_hallucinated_benchmark():
    f = _F("GM", "Gross margin 18% versus an industry median of 50%.")  # engine 33.2
    s = verify_findings([f], _RATIOS)
    assert f.benchmark_verification == "conflict"
    assert s["benchmark_conflicts"] == 1
    assert "GM" in s["benchmark_conflict_titles"]


def test_benchmark_within_tolerance_is_confirmed():
    # 32% cited vs 33.2% engine -> within 2pp tolerance -> confirmed (not a conflict)
    f = _F("GM", "Gross margin 18% against sector benchmark 32%.")
    verify_findings([f], _RATIOS)
    assert f.benchmark_verification == "confirmed"


def test_no_benchmark_cited_is_not_checked():
    f = _F("GM", "Gross margin is 18%.")
    s = verify_findings([f], _RATIOS)
    assert not hasattr(f, "benchmark_verification")
    assert s["benchmark_checked"] == 0


def test_days_benchmark_tolerant():
    # "54 vs 30 sector norm" -> firm 54, benchmark 30 vs engine 35 -> within 10-day tolerance
    f = _F("DD", "Debtor Days 54 vs 30 sector norm")
    verify_findings([f], _RATIOS)
    assert f.benchmark_verification == "confirmed"


def test_summary_has_benchmark_fields():
    s = verify_findings([], _RATIOS)
    for k in ("benchmark_checked", "benchmark_confirmed", "benchmark_conflicts", "benchmark_conflict_titles"):
        assert k in s


def test_adversarial_never_crashes():
    weird = [
        _F("", ""), _F(None, None, None), _F("x", 123, []),
        _F("GM", "gross margin vs benchmark of"),  # anchor but no number
        _F("GM", "gross margin 18% sector 33% industry 50% norm 12%"),  # many numbers
    ]
    for ratios in (None, {}, _RATIOS, {"gross_margin": {"value": None, "benchmark": None}}):
        s = verify_findings(list(weird), ratios)
        assert isinstance(s, dict) and "benchmark_checked" in s
