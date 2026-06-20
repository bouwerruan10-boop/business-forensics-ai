"""
Granular expense line-item extraction — pulls individual operating-expense rows
from a firm's P&L / management-accounts text into {category, label, amount},
mapped to a canonical SA-SME expense taxonomy. Deterministic (regex + arithmetic).

Feeds the supplier-benchmarking engine. Degrades gracefully: if the financials
only give totals (no itemised rows), it returns [] and the engine says so.
"""

import re

# (canonical_key, display_label, [patterns], substitutable?)
# `substitutable` = a competitive supplier market exists (Layer B can suggest a switch);
# magnitude-only categories still get Layer A (spend-vs-benchmark) treatment.
_EXPENSE_LABELS = [
    ("bank_charges",        "Bank charges",                       [r"bank charges", r"bank fees", r"bank cost"], True),
    ("card_machine_fees",   "Card machine / merchant fees",       [r"card machine", r"merchant (?:fees|service|discount)", r"card commission", r"\bpos fees\b", r"speed ?point", r"point[- ]of[- ]sale fees", r"payment processing", r"acquiring fees"], True),
    ("telephone_data",      "Telephone, data & internet",         [r"telephone", r"\bphone\b", r"cell(?:phone)?", r"\bmobile\b", r"airtime", r"\bdata\b", r"internet", r"\bfibre\b", r"broadband", r"\bvoip\b", r"communication"], True),
    ("fuel",                "Fuel",                               [r"\bfuel\b", r"\bpetrol\b", r"\bdiesel\b", r"fuel (?:and|&) oil"], True),
    ("insurance",           "Insurance",                          [r"insurance", r"\bassurance\b", r"short[- ]term insurance", r"insurance premium"], True),
    ("accounting_software", "Accounting / software subscriptions", [r"accounting software", r"\bpastel\b", r"\bxero\b", r"\bsage\b", r"quickbooks", r"\bzoho\b", r"software (?:subscription|licen)", r"\bsaas\b", r"cloud software"], True),
    ("computer_it",         "Computer & IT",                      [r"computer (?:expenses|costs)", r"\bit (?:expenses|support|services)\b", r"\bhosting\b", r"\bdomain\b", r"\bhardware\b"], True),
    ("electricity",         "Electricity",                        [r"electricity", r"\beskom\b", r"\bpower\b"], True),
    ("water_rates",         "Water & municipal rates",            [r"water (?:and|&) sanitation", r"\bsanitation\b", r"rates (?:and|&) taxes", r"municipal"], False),
    ("rent",                "Rent & premises",                    [r"\brent\b", r"\brental\b", r"\blease\b", r"premises", r"occupanc"], False),
    ("security",            "Security",                           [r"\bsecurity\b", r"guarding", r"\balarm\b", r"\bcctv\b"], True),
    ("courier_postage",     "Courier & postage",                  [r"courier", r"\bpostage\b", r"\bfreight\b", r"\bshipping\b"], True),
    ("travel_accommodation","Travel & accommodation",             [r"\btravel\b", r"accommodation", r"\bhotel\b", r"\bflights?\b", r"subsistence"], False),
    ("marketing",           "Marketing & advertising",            [r"marketing", r"advertis", r"promotion", r"\bbranding\b"], False),
    ("professional_fees",   "Professional fees",                  [r"accounting fees", r"audit fees", r"legal fees", r"consult", r"professional fees", r"bookkeeping fees", r"secretarial fees"], True),
    ("repairs_maintenance", "Repairs & maintenance",              [r"repairs", r"maintenance", r"\bupkeep\b"], False),
    ("printing_stationery", "Printing & stationery",              [r"printing", r"stationery", r"office supplies"], True),
    ("cleaning",            "Cleaning & refuse",                  [r"cleaning", r"\brefuse\b", r"hygiene"], True),
    ("subscriptions",       "Subscriptions & memberships",        [r"subscriptions", r"memberships", r"\bdues\b", r"\blicen[cs]es?\b"], True),
    ("training",            "Training & development",             [r"\btraining\b", r"skills development", r"staff development"], False),
    ("payroll_salaries",    "Salaries & wages",                   [r"salaries", r"\bwages\b", r"\bpayroll\b", r"staff costs", r"employee costs", r"remuneration", r"directors.? (?:remuneration|emoluments)"], False),
]

_AMOUNT = re.compile(r"-?\(?\s*(?:r|zar|\$)?\s*\d{1,3}(?:[ ,]\d{3})*(?:\.\d{2})?\)?", re.I)
# lines that are totals/subtotals/section headers — don't double-count
_SKIP = re.compile(r"\btotal\b|\bsub[- ]?total\b|gross profit|net profit|operating profit|\brevenue\b|\bturnover\b|cost of sales", re.I)


def _amount(line: str):
    vals = []
    for tok in _AMOUNT.findall(line):
        digits = re.sub(r"[^\d.]", "", tok.replace(" ", ""))
        if digits and digits != ".":
            try:
                vals.append(float(digits))
            except ValueError:
                pass
    return max(vals) if vals else None  # the line amount (largest number on the row)


def extract_expense_lines(text: str) -> list:
    text = text or ""
    agg = {}
    order = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or _SKIP.search(s):
            continue
        low = s.lower()
        for key, label, pats, sub in _EXPENSE_LABELS:
            if any(re.search(p, low) for p in pats):
                amt = _amount(s)
                if amt is None or amt <= 0:
                    break
                if key in agg:
                    agg[key]["amount"] += amt
                else:
                    agg[key] = {"category": key, "label": label, "amount": amt,
                                "substitutable": sub, "raw": s[:80]}
                    order.append(key)
                break  # first (most specific) category wins for this row
    out = [agg[k] for k in order]
    for r in out:
        r["amount"] = round(r["amount"], 2)
    return out
