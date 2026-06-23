"""Deterministic corpus-currency monitor.

Makes the silent staleness of Imara's dated rule corpora VISIBLE. No web, no LLM: it reads
each corpus's AS_OF marker, derives the current date / SA tax year, and flags what's stale.
This is the 'detect' half of the future 'research proposes, human disposes' refresh engine
(see RESEARCH_CYCLE_ENGINE_FEASIBILITY.md) - it never changes any figure, only reports.
"""
import re
from datetime import date

STALE_MONTHS = 12   # month-keyed corpora older than this are flagged for review


def current_sa_tax_year(today=None):
    """SA tax year runs 1 March -> end Feb. June 2026 -> '2026/27'."""
    today = today or date.today()
    start = today.year if today.month >= 3 else today.year - 1
    return "{}/{}".format(start, str(start + 1)[-2:])


def _tax_year_label(s):
    m = re.search(r"(20\d\d)/(\d\d)", s or "")
    return m.group(0) if m else None


def _months_old(asof, today):
    m = re.match(r"(20\d\d)-(\d\d)", asof or "")
    if not m:
        return None
    return (today.year - int(m.group(1))) * 12 + (today.month - int(m.group(2)))


def corpus_status(today=None):
    """Report each dated corpus's freshness. Returns a JSON-safe dict; pure-deterministic."""
    today = today or date.today()
    from services import relocation_tax, funder_gates, sa_rates, supplier_catalog
    cur_ty = current_sa_tax_year(today)
    corpora = []

    # 1) tax-year-keyed corpus: stale if its labelled year != the current SA tax year
    tax_label = _tax_year_label(getattr(relocation_tax, "TAX_AS_OF", ""))
    tax_stale = bool(tax_label and tax_label != cur_ty)
    corpora.append({
        "corpus": "SA tax rates / rebates / brackets / efficiency levers",
        "module": "relocation_tax + sa_rates + tax_optimizer",
        "as_of": getattr(relocation_tax, "TAX_AS_OF", None),
        "labelled_tax_year": tax_label,
        "current_sa_tax_year": cur_ty,
        "stale": tax_stale,
        "note": ("Labelled {} but the current SA tax year is {} - refresh rates/rebates/brackets "
                 "from the latest budget (research-gated; human-approved diff).".format(tax_label, cur_ty)
                 if tax_stale else "Current with the SA tax year."),
    })

    # 2) month-keyed corpora: stale if older than STALE_MONTHS
    for name, module, label in (
        ("DFI funder gates (SEDFA/IDC/NEF/...)", "funder_gates", getattr(funder_gates, "AS_OF", None)),
        ("SA rates snapshot", "sa_rates", getattr(sa_rates, "AS_OF", None)),
        ("Supplier catalog", "supplier_catalog", getattr(supplier_catalog, "CATALOG_AS_OF", None)),
        ("Relocation / tax-residency corridors", "relocation_tax", getattr(relocation_tax, "AS_OF", None)),
    ):
        mo = _months_old(label, today)
        stale = bool(mo is not None and mo > STALE_MONTHS)
        corpora.append({
            "corpus": name, "module": module, "as_of": label, "months_old": mo, "stale": stale,
            "note": ("{} months old (> {}-month window) - review.".format(mo, STALE_MONTHS)
                     if stale else "Within the freshness window."),
        })

    stale_count = sum(1 for c in corpora if c["stale"])
    return {
        "checked_on": today.isoformat(),
        "current_sa_tax_year": cur_ty,
        "stale_count": stale_count,
        "any_stale": stale_count > 0,
        "corpora": corpora,
        "note": ("Deterministic freshness check only - it flags what to refresh, it never edits a "
                 "figure. Updating a corpus is a separate, sourced, human-approved step."),
    }
