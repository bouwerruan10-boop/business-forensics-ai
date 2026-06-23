"""Benchmark key resolution regression (v1.75).

Frontend dropdown values (e.g. "retail") must resolve to their proper sector
profile (retail_general) — NOT silently fall back to the generic "general"
benchmark. This locks the gross-margin-benchmark bug found during the user test
(retail was benchmarked at 37.8% general instead of 33.2% retail)."""
from services.benchmark_service import get_benchmarks, resolve_benchmark_key

# frontend dropdown key -> expected resolved profile key
_FRONTEND = {
    "retail": "retail_general",
    "manufacturing": "manufacturing",
    "construction": "construction",
    "professional": "professional_services",
    "hospitality": "hospitality_restaurant",
    "healthcare": "healthcare",
    "transport": "logistics_trucking",
    "agriculture": "agriculture",
    "mining": "mining",
    "technology": "technology_software",
    "financial": "financial_services",
    "general": "general",
}


def test_retail_resolves_to_retail_not_general():
    assert resolve_benchmark_key("retail") == "retail_general"
    gm = get_benchmarks("retail")["margins"]["gross_margin"]
    assert abs(gm - 0.332) < 1e-6, gm
    # the bug was: retail -> general (0.378)
    assert gm != get_benchmarks("general")["margins"]["gross_margin"]


def test_all_frontend_keys_resolve_to_proper_profile():
    for fe, expected in _FRONTEND.items():
        assert resolve_benchmark_key(fe) == expected, (fe, resolve_benchmark_key(fe))


def test_truly_unknown_keys_fall_back_to_general():
    # genuinely unmapped sectors (no profile, no keyword hit) -> general
    for fe in ("astrology", "zzz-nonsense", "time travel"):
        assert resolve_benchmark_key(fe) == "general"


def test_resolution_is_case_and_space_insensitive():
    assert resolve_benchmark_key("  ReTaIl ") == "retail_general"


def test_adversarial_inputs_never_crash():
    for bad in [None, "", 123, [], {}, "zzz-nonsense", "\x00😀"]:
        prof = get_benchmarks(bad)
        assert isinstance(prof, dict) and "margins" in prof


# ── v1.77: expanded industry dropdown + 6 new sourced profiles ─────────────────
import json as _json  # noqa: E402
from services.benchmark_service import industry_display_name  # noqa: E402

# the canonical keys the (expanded) frontend dropdown now emits
_DROPDOWN_KEYS = [
    "retail_general", "retail_grocery", "wholesale_distribution", "hospitality_restaurant",
    "hotel_accommodation", "manufacturing", "construction", "motor_trade", "logistics_trucking",
    "professional_services", "financial_services", "real_estate", "technology_software",
    "media_creative", "healthcare", "education", "personal_services", "security_services",
    "agriculture", "mining", "npo_social", "general",
]
_NEW_PROFILES = ["personal_services", "motor_trade", "security_services", "education", "media_creative", "npo_social"]


def test_every_dropdown_key_resolves_to_its_own_profile():
    general_gm = get_benchmarks("general")["margins"]["gross_margin"]
    for k in _DROPDOWN_KEYS:
        assert resolve_benchmark_key(k) == k, k  # exact, no alias hop
        if k != "general":
            assert get_benchmarks(k)["margins"]["gross_margin"] != general_gm, f"{k} falls to general"


def test_dropdown_keys_have_display_names():
    for k in _DROPDOWN_KEYS:
        dn = industry_display_name(k)
        assert dn and dn != "General Business" or k == "general"


def test_new_profiles_schema_complete():
    ind = _json.load(open("data/benchmarks.json", encoding="utf-8"))["industries"]
    for k in _NEW_PROFILES:
        p = ind[k]
        assert p.get("display_name") and p.get("keywords")
        for m in ("gross_margin", "operating_margin", "net_margin", "ebitda_margin"):
            assert isinstance(p["margins"][m], (int, float))
        for grp in ("efficiency", "cost_ratios", "liquidity", "leverage"):
            assert isinstance(p.get(grp), dict) and p[grp]


def test_new_profile_margins_are_sane():
    # gross >= operating >= net, and all within (0,1)
    for k in _NEW_PROFILES:
        m = get_benchmarks(k)["margins"]
        assert 0 < m["gross_margin"] <= 1
        assert m["gross_margin"] >= m["operating_margin"] >= m["net_margin"]


def test_old_bare_keys_still_resolve_backward_compat():
    assert resolve_benchmark_key("retail") == "retail_general"
    assert resolve_benchmark_key("hospitality") == "hospitality_restaurant"
    assert resolve_benchmark_key("transport") == "logistics_trucking"


def test_keyword_scan_maps_free_text_to_new_sectors():
    # an LLM/free-text industry hint should land on the right new profile via keywords
    assert resolve_benchmark_key("private security guarding") == "security_services"
    assert resolve_benchmark_key("hair salon and spa") == "personal_services"
    assert resolve_benchmark_key("panel beater workshop") == "motor_trade"


def test_new_profiles_are_enriched_to_match_established():
    ind = _json.load(open("data/benchmarks.json", encoding="utf-8"))["industries"]
    for k in _NEW_PROFILES:
        p = ind[k]
        tq = p.get("top_quartile", {})
        assert "net_margin" in tq, f"{k} top_quartile missing net_margin"
        assert tq["gross_margin"] >= tq["operating_margin"] >= tq["net_margin"]
        # at least one sector-specific KPI beyond the three margins
        assert len(set(tq) - {"gross_margin", "operating_margin", "net_margin"}) >= 1, k
        assert p.get("_source"), f"{k} missing _source provenance"
