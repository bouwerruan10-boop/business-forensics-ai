"""Tests for the deterministic SA tax-optimisation engine (legal planning).
Eligibility correctness + no overstatement of the headline saving. No LLM."""
from memory.shared_memory import SharedMemory
from services import sa_rates
from services.tax_optimizer import analyze_tax_optimization


def _mk(entity="Private Company (Pty) Ltd", turnover=5_000_000, headcount=8, figs=None):
    m = SharedMemory()
    m.entity_type = entity
    m.annual_revenue = turnover
    m.headcount = headcount
    m.currency = "ZAR"
    m.financial_figures = figs if figs is not None else {"net_profit": 400_000}
    return m


def _by_name(res):
    return {o["name"]: o for o in res["opportunities"]}


def test_sbc_quantified_for_eligible_company():
    r = analyze_tax_optimization(_mk())
    sbc = _by_name(r)["Small Business Corporation rates (Section 12E)"]
    assert sbc["quantified"] is True
    # flat 27% on 400k = 108,000; SBC = 26,198 -> saving 81,802
    assert sbc["est_saving_high"] == 81802 and r["total_saving_high"] == 81802


def test_sole_proprietor_gets_no_sbc():
    r = analyze_tax_optimization(_mk(entity="Sole Proprietor"))
    assert "Small Business Corporation rates (Section 12E)" not in _by_name(r)


def test_turnover_over_ceiling_no_sbc_no_turnovertax():
    r = analyze_tax_optimization(_mk(turnover=30_000_000))
    n = _by_name(r)
    assert "Small Business Corporation rates (Section 12E)" not in n
    assert "Turnover-tax option (micro business)" not in n


def test_loss_making_flags_sbc_but_does_not_quantify():
    r = analyze_tax_optimization(_mk(figs={"net_profit": -50_000}))
    sbc = _by_name(r)["Small Business Corporation rates (Section 12E)"]
    assert sbc["quantified"] is False and r["total_saving_high"] == 0


def test_missing_financials_flag_only():
    r = analyze_tax_optimization(_mk(figs={}))
    sbc = _by_name(r)["Small Business Corporation rates (Section 12E)"]
    assert sbc["quantified"] is False


def test_no_employees_no_eti():
    r = analyze_tax_optimization(_mk(headcount=0))
    assert "Employment Tax Incentive (ETI)" not in _by_name(r)


def test_eti_is_per_employee_not_aggregated():
    # ETI must NOT show a headcount-multiplied aggregate (avoids absurd "up to R3bn")
    r = analyze_tax_optimization(_mk(headcount=20, figs={"net_profit": 400_000}))
    eti = _by_name(r)["Employment Tax Incentive (ETI)"]
    assert eti["quantified"] is False and eti["est_saving_high"] == 0
    assert "per-employee" in eti["basis"].lower()
    assert r["total_saving_high"] == 81802   # only SBC in the headline


def test_unknown_entity_is_possibly_eligible():
    r = analyze_tax_optimization(_mk(entity="", figs={"net_profit": 200_000}))
    assert _by_name(r)["Small Business Corporation rates (Section 12E)"]["eligible"] == "possibly"


def test_operating_profit_fallback():
    r = analyze_tax_optimization(_mk(figs={"operating_profit": 300_000}))
    sbc = _by_name(r)["Small Business Corporation rates (Section 12E)"]
    assert sbc["quantified"] is True and "operating profit" in sbc["basis"]


def test_disclaimer_and_dating_present():
    r = analyze_tax_optimization(_mk())
    assert "not tax advice" in r["disclaimer"].lower()
    assert r["as_of"] == sa_rates.AS_OF and r["sbc_tax_year"] == sa_rates.SBC_TAX_YEAR


def test_empty_memory_is_safe():
    m = SharedMemory(); m.annual_revenue = 0; m.headcount = 0; m.financial_figures = {}
    r = analyze_tax_optimization(m)
    assert isinstance(r["opportunities"], list)  # never crashes


def test_legal_line_no_evasion_or_migration_content():
    """Structural guarantee: the engine only surfaces legal statutory reliefs —
    never loophole/evasion/migration/scheme language."""
    forbidden = ["loophole", "evasion", "evade", "offshore", "migrat", "relocat",
                 "scheme", "shelter", "conceal", "aggressive"]
    for ent, tn, hc, figs in [("Private Company (Pty) Ltd", 5_000_000, 8, {"net_profit": 400_000}),
                              ("Sole Proprietor", 800_000, 2, {"net_profit": 150_000}),
                              ("", 30_000_000, 50, {"net_profit": 2_000_000})]:
        m = _mk(entity=ent, turnover=tn, headcount=hc, figs=figs)
        r = analyze_tax_optimization(m)
        text = " ".join((o["name"] + o["basis"] + o["action"] + o["caveat"]).lower()
                        for o in r["opportunities"])
        assert not any(w in text for w in forbidden), ent


def test_only_named_statutory_reliefs_surface():
    r = analyze_tax_optimization(_mk())
    allowed = {"Small Business Corporation rates (Section 12E)",
               "Accelerated capital allowances (Section 12E)",
               "Employment Tax Incentive (ETI)", "Skills Development Levy position",
               "Turnover-tax option (micro business)",
               "Learnership allowance (Section 12H)",
               "Research & Development deduction (Section 11D)",
               "Energy & renewable-asset allowances (Section 12B / 12L)",
               "Doubtful-debt allowance (Section 11(j))",
               "Donations to PBOs (Section 18A)",
               "Further reliefs to review"}
    assert all(o["name"] in allowed for o in r["opportunities"]), \
        [o["name"] for o in r["opportunities"] if o["name"] not in allowed]


def test_non_sa_business_is_gated_out():
    """SA statutory reliefs must NOT surface for a non-SA taxpayer."""
    m = _mk()
    m.currency = "USD"; m.country = "United States"
    r = analyze_tax_optimization(m)
    assert r["available"] is False and r["opportunities"] == []

def test_sa_context_via_country_even_if_currency_blank():
    m = _mk()
    m.currency = ""; m.country = "South Africa"
    r = analyze_tax_optimization(m)
    assert r["available"] is True


def test_accounting_negative_loss_is_not_a_saving():
    # a loss written in accounting parens must not be read as a profit
    r = analyze_tax_optimization(_mk(figs={"net_profit": "(50,000)"}))
    sbc = _by_name(r)["Small Business Corporation rates (Section 12E)"]
    assert sbc["quantified"] is False and r["total_saving_high"] == 0
