"""
Curated SA supplier / expense-benchmark catalog — the deterministic data layer for
supplier benchmarking. Same discipline as sa_knowledge.py and macro_data.py:
curated, DATED, labelled indicative, with an explicit service-equivalence note.

Two honest data types are stored (no fabricated competitor rand figures):
  * benchmark_pct: a typical spend band as % of revenue (for Layer-A magnitude).
  * low_cost_providers + typical_savings_pct: named REAL lower-cost SA providers in
    the category and a typical savings band, so Layer-B suggests a credible switch
    and a rand RANGE off the firm's actual spend — always "verify current quotes".

The Bright Data live-fallback (supplier_live.py) can refresh/augment these with
cited current pricing when enabled; the curated layer is the always-on default.
"""

CATALOG_AS_OF = "2026-06"
_SRC = "Imara curated SA market reference (indicative — verify current pricing)"

# category -> reference data. benchmark_pct = (low, high) % of revenue (None if no
# defensible general band). typical_savings_pct = (low, high) fraction off the line
# if switching to a lower-cost provider at equivalent service.
CATALOG = {
    "bank_charges": {
        "benchmark_pct": (0.15, 0.6),
        "equivalence": "Business transactional account with card acceptance, comparable monthly transaction volume.",
        "low_cost_providers": ["TymeBank Business", "Bank Zero", "Capitec Business", "Discovery Bank Business"],
        "higher_cost_incumbents": ["fnb", "standard bank", "absa", "nedbank"],
        "typical_savings_pct": (0.25, 0.50),
    },
    "card_machine_fees": {
        "benchmark_pct": (0.3, 1.2),
        "equivalence": "Card-present acquiring at a comparable turnover; rate quoted as % of card turnover.",
        "low_cost_providers": ["Yoco", "iKhokha", "Stitch", "Ozow (EFT)", "SnapScan / Zapper (QR)"],
        "higher_cost_incumbents": ["bank", "traditional acquirer"],
        "typical_savings_pct": (0.15, 0.40),
    },
    "telephone_data": {
        "benchmark_pct": (0.3, 1.5),
        "equivalence": "Business voice + data / fibre line of comparable speed and cap.",
        "low_cost_providers": ["Afrihost", "Webafrica", "Rain", "Telkom LIT", "MTN Business deals"],
        "higher_cost_incumbents": ["vodacom", "mtn", "telkom mobile"],
        "typical_savings_pct": (0.15, 0.40),
    },
    "fuel": {
        "benchmark_pct": None,  # varies enormously by sector (logistics vs office)
        "equivalence": "Fleet fuel at comparable litres; saving via a fuel/fleet card with rebates, not a cheaper fuel price (regulated).",
        "low_cost_providers": ["WesBank Fuel/Fleet Card", "Standard Bank Fleet", "FNB Fuel rebates", "Discovery fuel rewards"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.02, 0.08),
    },
    "insurance": {
        "benchmark_pct": (0.3, 1.5),
        "equivalence": "Comparable business cover (assets, liability, BI) and excess structure — re-broke, don't just drop cover.",
        "low_cost_providers": ["King Price Business", "Naked", "OUTsurance Business", "PSG / broker re-quote"],
        "higher_cost_incumbents": ["santam", "old mutual", "hollard", "momentum"],
        "typical_savings_pct": (0.10, 0.30),
    },
    "accounting_software": {
        "benchmark_pct": (0.05, 0.4),
        "equivalence": "Cloud accounting for comparable users/features.",
        "low_cost_providers": ["Zoho Books", "Wave (free)", "Xero Starter", "Sage Accounting Start"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.20, 0.50),
    },
    "computer_it": {
        "benchmark_pct": (0.2, 1.5),
        "equivalence": "Comparable hosting / IT support scope.",
        "low_cost_providers": ["Afrihost / xneelo hosting", "managed-IT re-quote", "Google Workspace vs Microsoft 365 tier review"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.30),
    },
    "electricity": {
        "benchmark_pct": None,
        "equivalence": "Tariff is largely fixed (Eskom/municipal); 'switch' = efficiency, load-shifting, solar/PPA, or a tariff-structure review.",
        "low_cost_providers": ["Solar PPA providers (e.g. Wetility, GoSolr, Discovery Green)", "energy-efficiency audit", "tariff/notified-maximum-demand review"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.30),
    },
    "security": {
        "benchmark_pct": (0.2, 1.5),
        "equivalence": "Comparable guarding hours / armed-response + monitoring scope.",
        "low_cost_providers": ["re-tender to ADT / Fidelity / regional providers", "monitoring-only vs guarding mix review"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.25),
    },
    "courier_postage": {
        "benchmark_pct": (0.1, 1.0),
        "equivalence": "Comparable parcel size / SLA.",
        "low_cost_providers": ["The Courier Guy", "Pudo (lockers)", "uAfrica / Bob Go (rate aggregation)", "Aramex re-quote"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.35),
    },
    "professional_fees": {
        "benchmark_pct": (0.2, 1.5),
        "equivalence": "Comparable scope of accounting/audit/secretarial work.",
        "low_cost_providers": ["fixed-fee SME accounting practices", "scope/engagement-letter review", "outsourced bookkeeping"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.30),
    },
    "printing_stationery": {
        "benchmark_pct": (0.05, 0.5),
        "equivalence": "Comparable print volume; managed-print vs ad-hoc.",
        "low_cost_providers": ["managed-print contract review", "bulk online stationery (e.g. Takealot Business, Waltons)"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.10, 0.30),
    },
    "cleaning": {
        "benchmark_pct": (0.05, 0.6),
        "equivalence": "Comparable area / frequency.",
        "low_cost_providers": ["re-tender regional cleaning providers", "frequency review"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.08, 0.20),
    },
    "subscriptions": {
        "benchmark_pct": (0.05, 0.8),
        "equivalence": "Same tool category; audit for unused/duplicate SaaS seats.",
        "low_cost_providers": ["seat/licence audit (cancel unused)", "annual vs monthly billing", "tier downgrade review"],
        "higher_cost_incumbents": [],
        "typical_savings_pct": (0.15, 0.45),
    },
    # magnitude-only (no clean supplier substitution)
    "rent":             {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "marketing":        {"benchmark_pct": (1.0, 10.0), "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "repairs_maintenance": {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "travel_accommodation": {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "water_rates":      {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "training":         {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
    "payroll_salaries": {"benchmark_pct": None, "equivalence": None, "low_cost_providers": [], "higher_cost_incumbents": [], "typical_savings_pct": None},
}


def category_reference(category: str) -> dict:
    c = CATALOG.get(category)
    if not c:
        return {}
    return {**c, "as_of": CATALOG_AS_OF, "source": _SRC}
