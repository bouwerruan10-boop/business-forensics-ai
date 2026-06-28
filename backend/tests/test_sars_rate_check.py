"""SARS rate-currency checker tests: manifest, label-anchored parser, alert-only diff."""
from decimal import Decimal

from fastapi.testclient import TestClient

from services import sa_rates, relocation_tax
from services.sars_rate_manifest import manifest, PAGES
from services.sars_rate_check import check, diff_against_manifest, _extract, _parse_number


# ---- manifest integrity ----

def test_manifest_expected_reads_live_from_code():
    by = {e["key"]: e for e in manifest()}
    # expected must equal the live constant (no second source of truth)
    assert by["primary_rebate"]["expected"] == float(relocation_tax.SA_PRIMARY_REBATE)
    assert by["vat_rate"]["expected"] == float(sa_rates.VAT_RATE)
    assert by["cgt_inclusion_individual"]["expected"] == float(sa_rates.CGT_INCLUSION_INDIVIDUAL) * 100
    assert by["official_rate_of_interest"]["expected"] == float(sa_rates.OFFICIAL_RATE_OF_INTEREST)


def test_every_entry_has_sanity_range_and_page():
    for e in manifest():
        lo, hi = e["sanity"]
        assert lo < hi
        assert e["page"] in PAGES
        assert e["unit"] in ("percent", "zar")


# ---- number parsing + label-anchored extraction ----

def test_parse_number_sa_formats():
    assert _parse_number("7,75") == Decimal("7.75")        # comma decimal
    assert _parse_number("R50 000") == Decimal("50000")    # space thousands
    assert _parse_number("2,300,000") == Decimal("2300000")
    assert _parse_number("15%") == Decimal("15")
    assert _parse_number("nonsense") is None


def test_extract_percent_zar_and_million():
    assert _extract("the official rate of interest is 8.00% now", ["official rate of interest"], "percent") == Decimal("8.00")
    assert _extract("annual exclusion is R50 000", ["annual exclusion"], "zar") == Decimal("50000")
    assert _extract("compulsory if you exceed R1 million in 12-month", ["compulsory", "exceed", "12-month"], "zar") == Decimal("1000000")
    # value not near label -> None (honest, not a wrong grab)
    assert _extract("nothing relevant here", ["official rate of interest"], "percent") is None


# ---- the diff engine ----

def _sars_pages(official="7.75", interest="10.50"):
    return {
        "individuals": "Primary rebate R17 820. Secondary rebate R9 765. Tertiary rebate R3 249.",
        "vat": "VAT is levied at the standard rate of 15%. Registration is compulsory if taxable supplies exceed R2.3 million in any 12-month period.",
        "cgt": "The inclusion rate for individuals is 40%. The annual exclusion is R50 000.",
        "companies": "Companies are taxed at 27%. Trusts (other than a special trust) at 45%.",
        "eti": "The maximum monthly remuneration is R7 500.",
        "interest": "The official rate of interest is {}%. The interest rate on outstanding taxes is {}%.".format(official, interest),
    }


def test_all_current_when_pages_match_code():
    r = check(_sars_pages())
    assert r["status"] == "current"
    assert r["summary"]["drifted"] == 0
    assert r["summary"]["unparsed"] == 0


def test_drift_detected_and_reported():
    # SARS shows 8.00% / 10.25% but Imara has 7.75 / 10.50 -> two drifts flagged
    r = check(_sars_pages(official="8.00", interest="10.25"))
    assert r["status"] == "drift_detected"
    drift_keys = {m["key"] for m in r["mismatches"]}
    assert "official_rate_of_interest" in drift_keys
    assert "sars_interest_rate" in drift_keys
    off = next(m for m in r["mismatches"] if m["key"] == "official_rate_of_interest")
    assert off["expected"] == 7.75 and off["found"] == 8.0


def test_html_content_is_parsed():
    pages = {"vat": "<html><body><p>VAT is levied at the <b>standard rate</b> of 15%.</p></body></html>"}
    r = check(pages)
    assert any(m["key"] == "vat_rate" for m in r["matches"])


def test_missing_page_is_unparsed_not_a_pass():
    r = check({"vat": "VAT standard rate of 15%."})
    assert r["status"] in ("current", "drift_detected")   # vat parsed
    # the figures whose pages weren't supplied are unparsed, never silently passed
    assert r["summary"]["unparsed"] >= 10
    assert "alert-only" in r["note"].lower()


def test_engine_never_returns_a_figure_to_write():
    # the report is advisory only: no key that looks like an instruction to overwrite
    r = check(_sars_pages())
    assert "apply" not in r and "auto_update" not in r


def test_robust_to_hostile_input():
    assert check("x")["status"] == "no_values_parsed"
    assert check(None)["summary"]["unparsed"] == len(manifest())
    assert diff_against_manifest(12345)[2]      # all unparsed, no crash


# ---- endpoint (admin gate open when ADMIN_API_KEY unset in tests) ----

def test_endpoint_returns_report_on_supplied_content():
    import main
    client = TestClient(main.app)
    res = client.post("/api/admin/sars-rate-check", json={"page_contents": _sars_pages(official="8.00")})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "drift_detected"
    assert any(m["key"] == "official_rate_of_interest" for m in body["mismatches"])


def test_manifest_endpoint():
    import main
    client = TestClient(main.app)
    res = client.get("/api/admin/sars-rate-manifest")
    assert res.status_code == 200
    assert res.json()["count"] == len(manifest())


def test_fetch_rejects_non_allowlisted_url_without_network():
    # the polite fetch helper only touches the manifest's SARS pages — anything else
    # is refused before any network call (no crawler / no arbitrary URLs)
    from services.sars_fetch import fetch_page
    r = fetch_page("https://example.com/not-sars")
    assert r["ok"] is False and "allowlist" in r["error"].lower()
