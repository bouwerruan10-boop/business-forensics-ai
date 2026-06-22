"""Tests for the market-research agent's upgraded competitor extraction (v1.54):
the noise-filtering cleaner + the heuristic fallback. Deterministic; no LLM/network."""
from agents.market_research_agent import _clean_competitor_names as clean, MarketDeepDiveAgent

_ag = MarketDeepDiveAgent()


def test_cleaner_drops_listicle_generic_self_and_dupes():
    out = clean(
        ["Top 10 Best Retailers", "Best Retail Companies in", "Shoprite Holdings",
         "Pick n Pay Stores", "10 Leading Retail", "Mzansi Retail Group reviews",
         "Woolworths Holdings Limited", "Companies", "the best grocery", "Massmart",
         "Shoprite Holdings"],
        company_name="Mzansi Retail Group", industry="retail")
    assert "Shoprite Holdings" in out and "Pick n Pay Stores" in out and "Massmart" in out
    # listicle / generic / self-reference removed
    assert not any(x.lower().startswith(("top ", "best ", "10 ", "the best")) for x in out)
    assert "Companies" not in out
    assert all("mzansi retail group" not in x.lower() for x in out)
    # de-duped
    assert len(out) == len(set(x.lower() for x in out))


def test_cleaner_is_total_on_junk():
    assert clean(None) == []
    assert clean("not-a-list") == []
    assert clean([None, "  ", "AB", 123, ""]) == []           # too-short / blank / non-str dropped
    assert clean(["Top Companies", "Best Providers", "123"], industry="retail") == []
    out = clean(["X" * 200, "Acme Trading"])                  # over-long dropped, valid kept
    assert out == ["Acme Trading"]


def test_cleaner_caps_at_six():
    big = [f"Company {chr(65+i)} Holdings" for i in range(20)]
    assert len(clean(big)) == 6


def test_heuristic_extractor_uses_cleaner():
    serp = {"competitors": {"organic": [
        {"title": "Top 10 Best Retail Companies in South Africa", "snippet": "list"},
        {"title": "Shoprite Holdings Ltd", "snippet": "retailer"},
        {"title": "Acme Retail - About Us", "snippet": "the company itself"},
    ]}}
    out = _ag._extract_competitors(serp, "Acme Retail", "retail")
    assert "Shoprite Holdings Ltd" in out
    assert not any(c.lower().startswith("top ") for c in out)   # listicle dropped
    assert all("acme retail" not in c.lower() for c in out)     # self dropped


def test_visibility_is_finite_on_empty():
    score, sentiment = _ag._calculate_visibility({})
    assert score == 0 and sentiment == "unknown"
