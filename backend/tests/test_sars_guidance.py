"""SARS-process guidance reference tests."""
from services.sars_guidance import sars_process_guidance as g


def test_all_cards_well_formed():
    r = g()
    assert r["available"] is True and r["count"] == 6
    keys = {c["key"] for c in r["cards"]}
    assert keys == {"verification", "audit", "vdp", "record_keeping",
                    "suspension_of_payment", "payment_arrangement"}
    for c in r["cards"]:
        assert c["title"] and c["deadline"] and c["citation"].startswith("Tax Administration Act")
        assert c["do"] and c["dont"]


def test_topic_lookup():
    r = g("vdp")
    assert r["available"] is True
    assert "Voluntary Disclosure" in r["card"]["title"]
    assert "s225-233" in r["card"]["citation"]


def test_topic_lookup_is_case_insensitive():
    assert g("AUDIT")["card"]["key"] == "audit"


def test_unknown_topic_lists_options():
    r = g("bogus")
    assert r["available"] is False
    assert "vdp" in r["topics"]
