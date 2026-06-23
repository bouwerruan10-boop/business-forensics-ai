"""
Deterministic earnings normalization for bankability / deal-readiness.

Reddit research (r/Accounting "books aren't deal ready"; r/PersonalFinanceZA
"self employed bond frustrations") shows two audiences need the SAME thing: the
gap between TAX books and DEAL/LOAN books. Owners run personal + one-off
expenses through the business for tax; buyers and banks want those added back to
see true earnings (Adjusted EBITDA / Seller's Discretionary Earnings). SA banks
specifically ask for an accountant's letter of total owner compensation incl.
personal expenses the company pays, and warn against drawing a loan account
instead of a salary.

Deterministic: regex + arithmetic only. Amounts come from the uploaded financial
text — nothing is invented. Every add-back is INDICATIVE and labelled
"confirm with the owner". Output is decision-support, never an Imara Score input.
"""
import math
import re

__all__ = ["normalize_earnings", "detect_loan_account"]

# (canonical, label, [patterns], bucket)
#  bucket: "dna"  -> used to DERIVE EBITDA from operating profit (not added on top)
#          "one_off"        -> high-confidence add-back (non-recurring)
#          "owner_personal" -> discretionary / likely-personal (optimistic add-back)
_ADDBACK_LABELS = [
    ("depreciation",   "Depreciation",                  [r"depreciation"],                         "dna"),
    ("amortisation",   "Amortisation",                  [r"amorti[sz]ation"],                       "dna"),
    ("once_off",       "Once-off / non-recurring",      [r"once[- ]?off", r"non[- ]?recurring", r"exceptional item"], "one_off"),
    ("restructuring",  "Restructuring / retrenchment",  [r"restructur", r"retrench", r"severance"], "one_off"),
    ("legal_settle",   "Legal settlement / claim",      [r"legal settlement", r"settlement of claim", r"lawsuit settlement"], "one_off"),
    ("impairment",     "Impairment / loss on disposal", [r"impairment", r"loss on (?:disposal|sale)"], "one_off"),
    ("bad_debts",      "Bad debts written off (one-off)", [r"bad debts? written off", r"bad debt write[- ]?off"], "one_off"),
    ("donations",      "Donations / sponsorship / CSI", [r"donations?", r"\bcsi\b", r"sponsorship"], "one_off"),
    ("directors_rem",  "Directors' remuneration (discretionary portion)", [r"directors?[’' ]? (?:remuneration|emoluments|salaries|salary)", r"owner'?s? salary"], "owner_personal"),
    ("drawings",       "Owner drawings",                [r"\bdrawings\b", r"owner draw"], "owner_personal"),
    ("motor_vehicle",  "Motor vehicle (owner)",         [r"motor vehicle", r"vehicle expenses", r"\bcar expenses\b"], "owner_personal"),
    ("fuel",           "Fuel (owner portion)",          [r"\bfuel\b", r"\bpetrol\b", r"\bdiesel\b"], "owner_personal"),
    ("entertainment",  "Travel & entertainment (owner)", [r"entertainment", r"travel and entertainment", r"subsistence"], "owner_personal"),
    ("telephone",      "Telephone / cellphone (owner)", [r"telephone", r"cell ?phone", r"\bmobile\b", r"airtime"], "owner_personal"),
    ("home_office",    "Home office",                   [r"home office"], "owner_personal"),
]

_MONEY = re.compile(r"-?\(?\s*(?:R|ZAR)?\s*([0-9][0-9 ,]*\.?[0-9]{0,2})\)?")
_NOTES_HEADER = re.compile(r"notes? to the (?:annual )?financial statements", re.I)
_SKIP = re.compile(r"\btotal\b|\bsubtotal\b|gross profit|operating profit|net profit|profit before|profit after", re.I)


def _num(v):
    """Coerce possibly-string/None figure to float (defensive — see distress_score)."""
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            f = float(v)
        else:
            s = str(v).strip().replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", "")
            neg = s.startswith("(") and s.endswith(")")
            s = s.strip("()")
            f = float(s)
            if neg:
                f = -f
    except (ValueError, TypeError):
        return None
    return f if math.isfinite(f) else None  # reject NaN/inf -> keeps output JSON-compliant


def _first_amount(line):
    line = line.replace(" ", " ")
    for m in _MONEY.finditer(line):
        raw = m.group(1).replace(" ", "").replace(",", "")
        if not raw or raw == ".":
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        if v >= 1:
            return round(v, 2)
    return None


def _scan_addbacks(text):
    """Return the largest single matching row per add-back category (face of statement)."""
    text = text or ""
    agg = {}
    order = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if _NOTES_HEADER.search(s):
            break
        if _SKIP.search(s):
            continue
        low = s.lower()
        for key, label, pats, bucket in _ADDBACK_LABELS:
            if any(re.search(p, low) for p in pats):
                amt = _first_amount(s)
                if amt is None or amt <= 0:
                    break
                if key in agg:
                    if amt > agg[key]["amount"]:
                        agg[key]["amount"] = amt
                        agg[key]["raw"] = s[:90]
                else:
                    agg[key] = {"category": key, "label": label, "amount": amt,
                                "bucket": bucket, "raw": s[:90]}
                    order.append(key)
                break
    return [agg[k] for k in order]


def detect_loan_account(financial_text, legal_text=""):
    """SA: drawing a loan account instead of a salary triggers SARS risk AND breaks
    bank affordability scoring (no payslips). Deterministic keyword detection."""
    blob = ((financial_text or "") + "\n" + (legal_text or "")).lower()
    has_loan = bool(re.search(r"\bloan account\b|director'?s? loan|shareholder'?s? loan|\bdrawings\b", blob))
    has_salary = bool(re.search(r"\bsalary\b|salaries|\bpaye\b|remuneration|payslip|emolument", blob))
    if not has_loan:
        return {"flagged": False}
    level = "high" if not has_salary else "medium"
    detail = ("The owner appears to draw a loan account / drawings"
              + ("" if has_salary else " with no clear salary or PAYE")
              + ". Two consequences: (1) SARS can treat an overdrawn director's/shareholder loan as a "
              "deemed dividend or impute interest (s7C / s8F) if not on arm's-length terms; (2) banks "
              "score affordability off payslips and a regular salary — drawing a loan account leaves no "
              "salary record, which is a common reason self-employed applicants are declined.")
    fix = ("Pay yourself a regular PAYE salary (even a modest one) so there is a payslip trail, and have "
           "your accountant document total owner compensation incl. company-paid personal expenses for the bank.")
    return {"flagged": True, "level": level, "detail": detail, "fix": fix,
            "has_salary_evidence": has_salary}


def normalize_earnings(figures, financial_text, legal_text=""):
    """Indicative Adjusted EBITDA / SDE from detected owner + one-off add-backs.

    figures: the deterministic financial_figures dict (revenue, operating_profit, ebitda, ...).
    Returns a decision-support dict; never an Imara Score input.
    """
    figures = figures if isinstance(figures, dict) else {}
    candidates = _scan_addbacks(financial_text)
    loan_flag = detect_loan_account(financial_text, legal_text)

    ebitda = _num(figures.get("ebitda"))
    op = _num(figures.get("operating_profit"))
    dna_total = round(sum(c["amount"] for c in candidates if c["bucket"] == "dna"), 2)

    if ebitda is not None:
        basis = "reported"
        reported_ebitda = round(ebitda, 2)
    elif op is not None:
        basis = "estimated_from_operating_profit"
        reported_ebitda = round(op + dna_total, 2)  # EBITDA = EBIT + D&A
    else:
        reported_ebitda = None
        basis = "unavailable"

    # Add-backs ON TOP of EBITDA (exclude dna — already inside EBITDA).
    one_off = [c for c in candidates if c["bucket"] == "one_off"]
    owner = [c for c in candidates if c["bucket"] == "owner_personal"]
    one_off_total = round(sum(c["amount"] for c in one_off), 2)
    owner_total = round(sum(c["amount"] for c in owner), 2)

    add_backs = []
    for c in one_off:
        add_backs.append({"label": c["label"], "amount": c["amount"], "confidence": "high",
                          "note": "Non-recurring — standard add-back."})
    for c in owner:
        add_backs.append({"label": c["label"], "amount": c["amount"], "confidence": "owner-confirm",
                          "note": "Discretionary / likely-personal — confirm the owner-personal portion."})

    if reported_ebitda is None:
        return {
            "available": False,
            "reason": "Could not establish EBITDA (no EBITDA/operating-profit figure extracted). "
                      "Provide an income statement with operating profit to normalise earnings.",
            "add_back_candidates": add_backs,
            "loan_account_flag": loan_flag,
        }

    adj_low = round(reported_ebitda + one_off_total, 2)              # conservative
    adj_high = round(reported_ebitda + one_off_total + owner_total, 2)  # optimistic
    base = reported_ebitda if reported_ebitda else 0.0
    uplift_low = round((adj_low - reported_ebitda) / abs(base) * 100, 1) if base else 0.0
    uplift_high = round((adj_high - reported_ebitda) / abs(base) * 100, 1) if base else 0.0

    return {
        "available": True,
        "reported_ebitda": reported_ebitda,
        "ebitda_basis": basis,
        "add_backs": add_backs,
        "add_backs_total_conservative": one_off_total,
        "add_backs_total_optimistic": round(one_off_total + owner_total, 2),
        "adjusted_ebitda_low": adj_low,
        "adjusted_ebitda_high": adj_high,
        "uplift_pct_low": uplift_low,
        "uplift_pct_high": uplift_high,
        "loan_account_flag": loan_flag,
        "note": ("Indicative normalisation (Adjusted EBITDA / Seller's Discretionary Earnings). "
                 "Owner/personal add-backs need the owner to confirm the personal portion. This is "
                 "the 'deal-/loan-book' view buyers and banks look for vs the tax-optimised view — "
                 "decision-support, not an Imara Score input."),
    }
