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


def test_flags_tax_corpus_when_year_behind():
    # In June 2026 the SA tax year is 2026/27, but the corpus is labelled 2025/26 -> stale.
    st = corpus_status(date(2026, 6, 24))
    tax = next(c for c in st["corpora"] if "tax rates" in c["corpus"])
    assert tax["stale"] is True and "2026/27" in tax["note"]


def test_not_stale_inside_the_tax_year():
    # Within the 2025/26 tax year (e.g. Jan 2026) the 2025/26 corpus is current.
    st = corpus_status(date(2026, 1, 15))
    tax = next(c for c in st["corpora"] if "tax rates" in c["corpus"])
    assert tax["stale"] is False
