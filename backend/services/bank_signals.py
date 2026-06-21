"""
Bank-statement transaction intelligence — deterministic cash-flow signals from
the firm's uploaded bank statement text.

For thin-file SMEs (the SA norm) transaction/cash-flow behaviour is the single
highest-lift creditworthiness signal — exactly what a lender underwrites on. This
module extracts it by ARITHMETIC + keyword detection (no LLM), and degrades
gracefully when the statement is absent or unparseable. It is surfaced as
decision-support evidence and a deterministic bank_health_score; it does NOT
silently alter the Imara Score (same discipline as the macro overlay).

Robust, format-agnostic signals (the ones that survive messy text):
  - returned / bounced debit orders  ← strongest distress signal
  - overdraft / negative-balance evidence
  - debit-order load and bank-fee load
  - cash-flow direction (inflow vs outflow) where classifiable
  - activity cadence (transactions, months covered)
"""

import re

# ── patterns ──────────────────────────────────────────────────────────────
_DATE = re.compile(
    r"(?:\b\d{4}-\d{2}-\d{2}\b)"
    r"|(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)"
    r"|(?:\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)",
    re.I,
)
_YM = re.compile(r"\b(\d{4})-(\d{2})\b|\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_AMOUNT = re.compile(r"-?\(?\s*(?:r|zar|\$)?\s*\d{1,3}(?:[ ,]\d{3})*(?:\.\d{2})?\)?", re.I)

_BOUNCED = re.compile(
    r"\b(?:r/?d|returned|unpaid|insufficient\s+funds|refer\s+to\s+drawer|"
    r"dishonou?red|reversal|reversed|do\s+unpaid|debit\s+order\s+unpaid|"
    r"payment\s+returned|nsf)\b",
    re.I,
)
_DEBIT_ORDER = re.compile(r"\bdebit\s+order\b|\bdebitorder\b|\bdo\s+\d", re.I)
_FEE = re.compile(r"\b(?:bank\s+charge|service\s+fee|admin\s+fee|monthly\s+fee|"
                  r"transaction\s+fee|maintenance\s+fee|ledger\s+fee)\b", re.I)
_OVERDRAFT = re.compile(r"\boverdraft\b|\bo/?d\b|\bexcess\b", re.I)
_CREDIT_KW = re.compile(r"\b(?:credit|deposit|received|salary|wages|incoming|eft\s+in|"
                        r"\bcr\b|inflow|payment\s+from)\b", re.I)
_DEBIT_KW = re.compile(r"\b(?:debit|withdrawal|payment\s+to|purchase|paid|fee|charge|"
                       r"\bdr\b|outflow|pos\b|atm\b)\b", re.I)


def _to_float(tok: str):
    neg = "(" in tok or tok.strip().startswith("-")
    digits = re.sub(r"[^\d.]", "", tok.replace(" ", ""))
    if not digits or digits == ".":
        return None
    try:
        v = float(digits)
    except ValueError:
        return None
    return -v if neg else v


def _month_key(line: str):
    m = _YM.search(line)
    if not m:
        return None
    if m.group(1):
        return m.group(1) + "-" + m.group(2)
    yy = m.group(5)
    if len(yy) == 2:
        yy = "20" + yy
    return yy + "-" + m.group(4).zfill(2)


def analyze_bank_statement(text: str) -> dict:
    text = text or ""
    if len(text.strip()) < 40:
        return {"available": False, "reason": "No bank statement provided or too little text to analyse."}

    lines = [ln for ln in text.splitlines() if ln.strip()]
    txn_lines = [ln for ln in lines if _DATE.search(ln)]

    if len(txn_lines) < 3:
        return {"available": False,
                "reason": "Bank statement text found but too few dated transaction rows to analyse reliably."}

    months = sorted({mk for ln in txn_lines for mk in [_month_key(ln)] if mk})

    # Count distinct transaction ROWS that carry each signal (not raw keyword hits),
    # so a row with several distress words counts once.
    bounced = sum(1 for ln in txn_lines if _BOUNCED.search(ln))
    debit_orders = sum(1 for ln in txn_lines if _DEBIT_ORDER.search(ln))
    fees = sum(1 for ln in txn_lines if _FEE.search(ln))
    overdraft_hits = sum(1 for ln in txn_lines if _OVERDRAFT.search(ln))

    inflow = outflow = 0.0
    classified = 0
    largest_in = largest_out = 0.0
    balances = []
    month_inflow = {}
    for ln in txn_lines:
        amts = [v for v in (_to_float(t) for t in _AMOUNT.findall(ln)) if v is not None and abs(v) >= 1]
        if not amts:
            continue
        _mk = _month_key(ln)
        # Heuristic: the last number on a statement row is usually the running balance.
        if len(amts) >= 2:
            balances.append(amts[-1])
            txn_amt = max(amts[:-1], key=abs)
        else:
            txn_amt = amts[0]
        is_credit = bool(_CREDIT_KW.search(ln))
        is_debit = bool(_DEBIT_KW.search(ln))
        if is_credit and not is_debit:
            inflow += abs(txn_amt); classified += 1
            largest_in = max(largest_in, abs(txn_amt))
            if _mk: month_inflow[_mk] = month_inflow.get(_mk, 0.0) + abs(txn_amt)
        elif is_debit and not is_credit:
            outflow += abs(txn_amt); classified += 1
            largest_out = max(largest_out, abs(txn_amt))
        elif txn_amt < 0:
            outflow += abs(txn_amt); classified += 1
            largest_out = max(largest_out, abs(txn_amt))
        elif txn_amt > 0:
            inflow += abs(txn_amt); classified += 1
            largest_in = max(largest_in, abs(txn_amt))
            if _mk: month_inflow[_mk] = month_inflow.get(_mk, 0.0) + abs(txn_amt)

    negative_balance_rows = sum(1 for b in balances if b < 0)
    min_balance = min(balances) if balances else None
    _plaus_bal = [b for b in balances if abs(b) < 1e10]  # drop merge/parse artefacts
    avg_balance = round(sum(_plaus_bal) / len(_plaus_bal), 2) if _plaus_bal else None
    _dep = [v for v in month_inflow.values() if 0 < v < 1e10]
    deposit_consistency = None
    if len(_dep) >= 2:
        import statistics
        _mean = sum(_dep) / len(_dep)
        if _mean > 0:
            _cv = statistics.pstdev(_dep) / _mean
            deposit_consistency = ('consistent' if _cv < 0.35 else 'variable' if _cv < 0.6 else 'erratic')
    flow_confident = classified >= max(3, int(0.4 * len(txn_lines)))
    net_flow = (inflow - outflow) if flow_confident else None

    # ── deterministic bank-health score (0-100, decision-support, NOT an Imara component) ──
    score = 100
    drivers = []
    if bounced:
        pen = min(45, 15 * bounced)
        score -= pen
        drivers.append(f"{bounced} returned/bounced debit order signal(s) — strong distress indicator (−{pen})")
    if negative_balance_rows or overdraft_hits:
        n = negative_balance_rows or overdraft_hits
        pen = min(25, 8 * n)
        score -= pen
        drivers.append(f"{n} negative-balance / overdraft signal(s) (−{pen})")
    if net_flow is not None and net_flow < 0:
        score -= 15
        drivers.append("Net cash outflow over the period (−15)")
    if len(months) < 3:
        score -= 10
        drivers.append(f"Only {len(months)} month(s) of statements — limited history (−10)")
    if debit_orders and bounced and bounced >= max(1, debit_orders // 3):
        score -= 10
        drivers.append("High share of debit orders failing (−10)")
    score = max(0, min(100, score))
    tier = "strong" if score >= 75 else "adequate" if score >= 50 else "weak"

    strengths = []
    if not bounced:
        strengths.append("No returned/bounced debit orders detected.")
    if net_flow is not None and net_flow > 0:
        strengths.append("Net cash inflow over the period.")
    if len(months) >= 3:
        strengths.append(f"{len(months)} months of statement history.")
    if min_balance is not None and min_balance >= 0:
        strengths.append("No negative balances observed.")

    return {
        "available": True,
        "period_months": len(months),
        "months": months,
        "transactions_analysed": len(txn_lines),
        "returned_debit_orders": bounced,
        "debit_order_count": debit_orders,
        "bank_fee_lines": fees,
        "overdraft_signals": overdraft_hits,
        "negative_balance_rows": negative_balance_rows,
        "min_balance": (round(min_balance, 2) if min_balance is not None else None),
        "avg_balance": avg_balance,
        "deposit_consistency": deposit_consistency,
        "inflow": round(inflow, 2) if flow_confident else None,
        "outflow": round(outflow, 2) if flow_confident else None,
        "net_flow": round(net_flow, 2) if net_flow is not None else None,
        "largest_inflow": round(largest_in, 2) if largest_in else None,
        "largest_outflow": round(largest_out, 2) if largest_out else None,
        "flow_confidence": "ok" if flow_confident else "low (debit/credit direction not reliably classifiable from text)",
        "bank_health_score": score,
        "bank_health_tier": tier,
        "risk_drivers": drivers,
        "strengths": strengths,
        "note": ("Deterministic cash-flow signals from the bank statement (arithmetic + keyword "
                 "detection, no AI). Decision-support evidence for a lender's affordability "
                 "assessment; not a component of the Imara Score."),
    }
