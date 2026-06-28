"""Deterministic corpus-currency monitor tests."""
import json
from datetime import date
from services.corpus_currency import current_sa_tax_year, corpus_status


def test_sa_tax_year_boundary():
    assert current_sa_tax_year(date(2026, 2, 28)) == "2025/26"   # before 1 March -> prior year
    assert current_sa_tax_year(date(2026, 3, 1)) == "2026/27"    # 1 March -> new year
    assert current_sa_tax_year(date(2025, 7, 1)) == "2025/26"


def test_corpus_status_structure_and_json_safe():
    st = corpus_status(date(2026, 6, 24))
    assert st["current_sa_tax_year"] == "2026/27"
    assert isinstance(st["corpora"], list) and len(st["corpora"]) >= 4
    for c in st["corpora"]:
        assert "corpus" in c and "module" in c and "as_of" in c and "stale" in c and "note" in c
    json.dumps(st)  # must be JSON-safe
    assert isinstance(st["any_stale"], bool) and isinstance(st["stale_count"], int)


def test_tax_corpus_staleness_tracks_label_vs_current_year():
    """Stale is flagged exactly when the corpus's labelled tax year differs from the current
    SA tax year - robust to whatever year the corpus currently holds (so it survives refreshes)."""
    import re
    from services import relocation_tax
    from services.corpus_currency import current_sa_tax_year
    label = re.search(r"20\d\d/\d\d", relocation_tax.TAX_AS_OF).group(0)
    for d in (date(2026, 6, 24), date(2026, 1, 15), date(2027, 4, 1)):
        st = corpus_status(d)
        tax = next(c for c in st["corpora"] if "tax rates" in c["corpus"])
        assert tax["stale"] == (label != current_sa_tax_year(d))


def test_refresh_log_present_and_sourced():
    import json
    from services.corpus_refresh import corpus_refresh_log
    log = corpus_refresh_log()
    assert log["count"] >= 1
    r0 = log["refreshes"][0]
    assert r0["to_tax_year"] == "2026/27" and r0["applied"] is True and r0["sources"]
    # the Budget-2026 primary-rebate refresh is recorded (search all entries — order-independent)
    assert any(c["field"] == "primary_rebate" and c["to"] == 17820
               for r in log["refreshes"] for c in r["changes"])
    json.dumps(log)


def test_tax_corpus_now_current_after_refresh():
    from datetime import date
    from services.corpus_currency import corpus_status
    st = corpus_status(date(2026, 6, 24))
    tax = next(c for c in st["corpora"] if "tax rates" in c["corpus"])
    assert tax["stale"] is False   # refreshed to 2026/27
