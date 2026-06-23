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


def test_keys_without_a_profile_fall_back_to_general():
    # education + media have no dedicated profile -> general is correct
    for fe in ("education", "media"):
        assert resolve_benchmark_key(fe) == "general"


def test_resolution_is_case_and_space_insensitive():
    assert resolve_benchmark_key("  ReTaIl ") == "retail_general"


def test_adversarial_inputs_never_crash():
    for bad in [None, "", 123, [], {}, "zzz-nonsense", "\x00😀"]:
        prof = get_benchmarks(bad)
        assert isinstance(prof, dict) and "margins" in prof
