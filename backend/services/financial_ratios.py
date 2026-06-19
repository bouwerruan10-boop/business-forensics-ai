"""
Deterministic financial-ratio engine.

The specialist agents are LLMs — every ZAR figure they emit is GENERATED text.
For a bankability product that is a hallucination risk. This module computes the
core credit/health ratios in plain Python directly from the uploaded financials,
so the headline numbers a lender sees are ARITHMETIC, not generation. Each metric
carries the exact source figures it was derived from, for traceability.

Pure functions, no API, no side effects — fully unit-testable.
"""
import re
from services.benchmark_service import get_benchmarks

# ── Number parsing ────────────────────────────────────────────────────────

_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6,
         "bn": 1e9, "billion": 1e9}


def parse_amount(raw: str):
    """Parse a messy money string into a float. Returns None if not a number.
    Handles: 'R 1 200 000', '1,200,000', '1.2m', '(500)' (negative), 'R8 000k'."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace("r", "").replace("$", "").replace("zar", "").replace("%", "")
    # capture trailing multiplier suffix (m / k / million ...)
    mult = 1.0
    msuf = re.search(r"([a-z]+)\s*$", s)
    if msuf and msuf.group(1) in _MULT:
        mult = _MULT[msuf.group(1)]
        s = s[: msuf.start()].strip()
    # keep digits, separators, sign, decimal point
    s = re.sub(r"[^0-9.,\- ]", "", s).strip()
    if not re.search(r"\d", s):
        return None
    # spaces are thousand separators
    s = s.replace(" ", "")
    # if both , and . present, assume , = thousands, . = decimal
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        # comma decimal (e.g. "1,5") only if single comma with <=2 trailing digits
        if re.match(r"^-?\d+,\d{1,2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        val = float(s) * mult
    except ValueError:
        return None
    return -val if neg else val


# ── Line-item extraction ──────────────────────────────────────────────────
# Ordered so more specific labels win (e.g. "gross profit" before "profit").
_LABELS = [
    ("revenue",            [r"\brevenue\b", r"\bturnover\b", r"\btotal sales\b", r"\bsales\b", r"\btotal income\b"]),
    ("cogs",               [r"cost of goods sold", r"cost of sales", r"\bcogs\b"]),
    ("gross_profit",       [r"gross profit"]),
    ("operating_profit",   [r"operating profit", r"\bebit\b", r"profit from operations"]),
    ("ebitda",             [r"\bebitda\b"]),
    ("net_profit",         [r"net profit", r"profit after tax", r"profit for the (?:year|period)", r"net income"]),
    ("opex",               [r"operating expenses", r"\bopex\b", r"overheads", r"operating costs"]),
    ("interest",           [r"interest expense", r"finance costs?", r"interest paid"]),
    ("current_assets",     [r"current assets"]),
    ("current_liabilities",[r"current liabilities"]),
    ("inventory",          [r"\binventory\b", r"\bstock\b", r"inventories"]),
    ("receivables",        [r"trade receivables", r"accounts receivable", r"trade debtors", r"\bdebtors\b", r"receivables"]),
    ("payables",           [r"trade payables", r"accounts payable", r"trade creditors", r"\bcreditors\b", r"payables"]),
    ("total_debt",         [r"interest.bearing (?:debt|borrowings)", r"total (?:debt|borrowings)", r"\bborrowings\b", r"long.term loans?"]),
    ("equity",             [r"shareholders.? equity", r"total equity", r"\bequity\b", r"net assets"]),
    ("cash",               [r"cash and cash equivalents", r"cash and equivalents", r"\bcash\b"]),
]

_NUM = r"[-(]?\s*(?:r|zar|\$)?\s*[\d][\d.,\s]*\d(?:\s*(?:k|m|mn|bn|million|thousand|billion))?\)?"


def extract_financials(text: str) -> dict:
    """Best-effort extraction of labelled line items from messy statement text.
    Returns {field: float}. Only fields confidently found are included."""
    out = {}
    if not text:
        return out
    low = text.lower()
    for field, patterns in _LABELS:
        if field in out:
            continue
        for pat in patterns:
            # number appearing AFTER the label on the same line/segment
            m = re.search(pat + r"[^\n\d(-]{0,40}?(" + _NUM + r")", low)
            if m:
                val = parse_amount(m.group(1))
                if val is not None:
                    out[field] = val
                    break
    # Derive gross_profit if revenue & cogs known but gross_profit absent
    if "gross_profit" not in out and "revenue" in out and "cogs" in out:
        out["gross_profit"] = out["revenue"] - out["cogs"]
    return out


# ── Ratio computation ─────────────────────────────────────────────────────

def _src(**figs):
    return " ; ".join("{}={:,.0f}".format(k, v) for k, v in figs.items())


def compute_ratios(figures: dict, industry_key: str = "general", annual_revenue: float = 0.0) -> dict:
    """Compute credit/health ratios from extracted figures + profile revenue.
    Each result: {value, unit, benchmark, status, source}. Only computable ones returned."""
    f = dict(figures or {})
    if annual_revenue and "revenue" not in f:
        f["revenue"] = float(annual_revenue)
    bm = get_benchmarks(industry_key) or {}
    margins = bm.get("margins", {}); liq = bm.get("liquidity", {})
    lev = bm.get("leverage", {}); eff = bm.get("efficiency", {})

    rev = f.get("revenue")
    cogs = f.get("cogs")
    gp = f.get("gross_profit")
    if gp is None and rev and cogs is not None:
        gp = rev - cogs
    ratios = {}

    def add(key, label, value, unit, benchmark, status, source):
        ratios[key] = {"label": label, "value": round(value, 2) if value is not None else None,
                       "unit": unit, "benchmark": benchmark, "status": status, "source": source}

    def rag(v, good, warn, higher_better=True):
        if higher_better:
            return "good" if v >= good else "warning" if v >= warn else "critical"
        return "good" if v <= good else "warning" if v <= warn else "critical"

    # Gross margin
    if gp is not None and rev:
        gm = gp / rev
        b = margins.get("gross_margin", 0.30)
        add("gross_margin", "Gross Margin", gm * 100, "%", round(b * 100, 1),
            rag(gm, b, b * 0.7), _src(gross_profit=gp, revenue=rev))
    # Net margin
    if f.get("net_profit") is not None and rev:
        nm = f["net_profit"] / rev
        b = margins.get("net_margin", 0.05)
        add("net_margin", "Net Margin", nm * 100, "%", round(b * 100, 1),
            rag(nm, b, 0), _src(net_profit=f["net_profit"], revenue=rev))
    # Operating margin
    if f.get("operating_profit") is not None and rev:
        om = f["operating_profit"] / rev
        b = margins.get("operating_margin", 0.08)
        add("operating_margin", "Operating Margin", om * 100, "%", round(b * 100, 1),
            rag(om, b, 0), _src(operating_profit=f["operating_profit"], revenue=rev))
    # Current ratio
    if f.get("current_assets") and f.get("current_liabilities"):
        cr = f["current_assets"] / f["current_liabilities"]
        add("current_ratio", "Current Ratio", cr, "x", liq.get("current_ratio", 1.5),
            rag(cr, 1.5, 1.0), _src(current_assets=f["current_assets"], current_liabilities=f["current_liabilities"]))
        # Quick ratio
        if f.get("inventory") is not None:
            qr = (f["current_assets"] - f["inventory"]) / f["current_liabilities"]
            add("quick_ratio", "Quick Ratio", qr, "x", liq.get("quick_ratio", 0.8),
                rag(qr, 1.0, 0.7), _src(current_assets=f["current_assets"], inventory=f["inventory"],
                                        current_liabilities=f["current_liabilities"]))
    # Debtor days
    if f.get("receivables") and rev:
        dd = f["receivables"] / rev * 365
        add("debtor_days", "Debtor Days", dd, "days", eff.get("debtor_days", 35),
            rag(dd, 35, 50, higher_better=False), _src(receivables=f["receivables"], revenue=rev))
    # Creditor days
    if f.get("payables") and (cogs or rev):
        base = cogs or rev
        cd = f["payables"] / base * 365
        add("creditor_days", "Creditor Days", cd, "days", eff.get("creditor_days", 35),
            "good" if 25 <= cd <= 60 else "warning", _src(payables=f["payables"], **({"cogs": cogs} if cogs else {"revenue": rev})))
    # Inventory days
    if f.get("inventory") and cogs:
        idd = f["inventory"] / cogs * 365
        add("inventory_days", "Inventory Days", idd, "days", eff.get("inventory_turnover_days", 45),
            rag(idd, eff.get("inventory_turnover_days", 45), eff.get("inventory_turnover_days", 45) * 1.5, higher_better=False),
            _src(inventory=f["inventory"], cogs=cogs))
    # Gearing (debt-to-equity)
    if f.get("total_debt") is not None and f.get("equity") and f["equity"] != 0:
        de = f["total_debt"] / f["equity"]
        add("debt_to_equity", "Debt-to-Equity (Gearing)", de, "x", lev.get("debt_to_equity", 1.0),
            rag(de, lev.get("debt_to_equity", 1.0), lev.get("debt_to_equity", 1.0) * 2, higher_better=False),
            _src(total_debt=f["total_debt"], equity=f["equity"]))
    # Interest coverage (proxy for debt-service capacity)
    if f.get("operating_profit") is not None and f.get("interest"):
        ic = f["operating_profit"] / f["interest"]
        add("interest_coverage", "Interest Coverage", ic, "x", lev.get("interest_coverage", 4.0),
            rag(ic, 3.0, 1.5), _src(operating_profit=f["operating_profit"], interest=f["interest"]))
    return ratios


# ── Deterministic fundamentals score ──────────────────────────────────────

def fundamentals_score(ratios: dict, industry_key: str = "general") -> dict:
    """Blend available computed ratios into a 0-100 fundamentals score.
    Returns {score, components_used, available}. None-safe; only uses what exists."""
    if not ratios:
        return {"score": None, "components_used": 0, "available": False}
    bm = get_benchmarks(industry_key) or {}
    margins = bm.get("margins", {})

    def clamp(x):
        return max(0.0, min(100.0, x))

    parts = []
    # Gross margin vs benchmark median (median -> 70, double median -> 100, zero -> 20)
    if "gross_margin" in ratios and ratios["gross_margin"]["value"] is not None:
        gm = ratios["gross_margin"]["value"] / 100.0
        b = margins.get("gross_margin", 0.30) or 0.30
        parts.append(clamp(20 + (gm / b) * 50))
    if "net_margin" in ratios and ratios["net_margin"]["value"] is not None:
        nm = ratios["net_margin"]["value"] / 100.0
        b = margins.get("net_margin", 0.05) or 0.05
        parts.append(clamp(40 + (nm / b) * 40))
    if "current_ratio" in ratios and ratios["current_ratio"]["value"] is not None:
        cr = ratios["current_ratio"]["value"]
        parts.append(clamp((cr / 1.5) * 70))          # 1.5x -> 70
    if "debt_to_equity" in ratios and ratios["debt_to_equity"]["value"] is not None:
        de = ratios["debt_to_equity"]["value"]
        parts.append(clamp(100 - de * 40))            # 0 -> 100, 1.0x -> 60, 2.5x -> 0
    if "debtor_days" in ratios and ratios["debtor_days"]["value"] is not None:
        dd = ratios["debtor_days"]["value"]
        parts.append(clamp(100 - max(0, dd - 20) * 1.5))  # <=20 days -> 100
    if "interest_coverage" in ratios and ratios["interest_coverage"]["value"] is not None:
        ic = ratios["interest_coverage"]["value"]
        parts.append(clamp((ic / 4.0) * 70))          # 4x -> 70

    if not parts:
        return {"score": None, "components_used": 0, "available": False}
    return {"score": int(round(sum(parts) / len(parts))),
            "components_used": len(parts), "available": True}
