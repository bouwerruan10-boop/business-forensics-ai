"""
Alternative-data signals — thin/no-file cash-flow evidence for informal SMEs.

Dossier M2 (the one genuinely missing capability): Imara scores firms that upload financials /
bank statements, so thin/no-file informal firms fall through to `available: False`. A large share
of SA SMMEs transact through mobile money and POS/card settlements, not a formal bank account.

This module reads a mobile-money / POS-settlement statement (same upload+parse path as bank
statements) and emits a deterministic thin-file `altdata_health_score` analogous to
`bank_signals.bank_health_score` — settlement cadence + consistency, gross throughput, and the
reversal/chargeback distress signal. It is an OVERLAY (decision-support evidence), NOT an Imara
Score input — same discipline as the bank-signals + macro overlays. Arithmetic + keyword detection,
no LLM; degrades to `available: False` when the text isn't an alt-data statement.
"""
import math
import re
import statistics

# Channel markers that distinguish an alt-data statement from a normal bank statement.
_ALT = re.compile(r"\b(?:settlement|payout|merchant\s+settlement|momo|m-?pesa|mobile\s+money|"
                  r"e-?wallet|wallet|snapscan|yoco|zapper|ikhokha|speedpoint|instant\s+money|airtime)\b", re.I)
_POS = re.compile(r"\b(?:pos|point\s+of\s+sale|card|tap|swipe|qr)\b", re.I)
_REVERSAL = re.compile(r"\b(?:reversal|reversed|charge\s*back|chargeback|refund|disputed|declined)\b", re.I)
_INFLOW = re.compile(r"\b(?:settlement|payout|deposit|received|credit|sale|takings|incoming|cr)\b", re.I)
_DATE = re.compile(r"(?:\b\d{4}-\d{2}-\d{2}\b)|(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)"
                   r"|(?:\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)", re.I)
_YM = re.compile(r"\b(\d{4})-(\d{2})\b|\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_AMOUNT = re.compile(r"-?\(?\s*(?:r|zar|\$)?\s*\d{1,3}(?:[ ,]\d{3})*(?:\.\d{2})?\)?", re.I)


def _to_float(tok):
    neg = "(" in tok or tok.strip().startswith("-")
    digits = re.sub(r"[^\d.]", "", tok.replace(" ", ""))
    if not digits or digits == ".":
        return None
    try:
        v = float(digits)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    return -v if neg else v


def _month_key(line):
    m = _YM.search(line)
    if not m:
        return None
    if m.group(1):
        return m.group(1) + "-" + m.group(2)
    yy = m.group(5)
    if len(yy) == 2:
        yy = "20" + yy
    return yy + "-" + m.group(4).zfill(2)


def analyze_altdata_statement(text: str) -> dict:
    text = text or ""
    if len(text.strip()) < 40:
        return {"available": False, "reason": "No statement text to analyse."}
    lines = [ln for ln in text.splitlines() if ln.strip()]
    alt_lines = [ln for ln in lines if _ALT.search(ln)]
    # Require a real density of alt-data markers so a normal bank statement doesn't trigger this.
    if len(alt_lines) < 3:
        return {"available": False,
                "reason": "Not a mobile-money / POS-settlement statement (too few alt-data markers)."}

    txn_lines = [ln for ln in lines if _DATE.search(ln)] or alt_lines
    months = sorted({mk for ln in txn_lines for mk in [_month_key(ln)] if mk})
    channel = ("mobile_money" if sum(1 for ln in alt_lines if re.search(r"momo|m-?pesa|mobile\s+money|wallet|airtime", ln, re.I))
               >= sum(1 for ln in alt_lines if _POS.search(ln)) else "pos_card")
    reversals = sum(1 for ln in txn_lines if _REVERSAL.search(ln))

    gross_inflow = 0.0
    settlements = 0
    month_inflow = {}
    for ln in txn_lines:
        if not _INFLOW.search(ln):
            continue
        amts = [v for v in (_to_float(t) for t in _AMOUNT.findall(ln)) if v is not None and 1 <= abs(v) < 1e10]
        if not amts:
            continue
        amt = max(amts, key=abs)
        gross_inflow += abs(amt)
        settlements += 1
        mk = _month_key(ln)
        if mk:
            month_inflow[mk] = month_inflow.get(mk, 0.0) + abs(amt)

    _dep = [v for v in month_inflow.values() if 0 < v < 1e10]
    consistency = None
    if len(_dep) >= 2:
        mean = sum(_dep) / len(_dep)
        if mean > 0:
            cv = statistics.pstdev(_dep) / mean
            consistency = ("consistent" if cv < 0.35 else "variable" if cv < 0.6 else "erratic")

    # ── deterministic alt-data health score (0-100; OVERLAY, not an Imara component) ──
    score, drivers, strengths = 100, [], []
    if reversals:
        pen = min(40, 12 * reversals)
        score -= pen
        drivers.append(f"{reversals} reversal/chargeback signal(s) — the alt-data distress indicator (−{pen})")
    if len(months) < 3:
        score -= 15
        drivers.append(f"Only {len(months)} month(s) of settlement history — limited track record (−15)")
    if settlements < 10:
        score -= 10
        drivers.append(f"Only {settlements} settlement/inflow rows — thin activity (−10)")
    if consistency == "erratic":
        score -= 12
        drivers.append("Settlement volume is erratic month-to-month (−12)")
    elif consistency == "variable":
        score -= 5
        drivers.append("Settlement volume is variable month-to-month (−5)")
    score = max(0, min(100, score))
    tier = "strong" if score >= 75 else "adequate" if score >= 50 else "weak"

    if not reversals:
        strengths.append("No reversals/chargebacks detected.")
    if len(months) >= 3:
        strengths.append(f"{len(months)} months of settlement history.")
    if consistency == "consistent":
        strengths.append("Consistent settlement volume month-to-month.")
    if settlements >= 30:
        strengths.append(f"{settlements} settlement/inflow events — active throughput.")

    return {
        "available": True,
        "channel": channel,
        "period_months": len(months),
        "months": months,
        "transactions_analysed": len(txn_lines),
        "alt_markers": len(alt_lines),
        "settlement_inflow_rows": settlements,
        "gross_inflow": round(gross_inflow, 2) if gross_inflow else None,
        "settlement_consistency": consistency,
        "reversals": reversals,
        "altdata_health_score": score,
        "altdata_health_tier": tier,
        "risk_drivers": drivers,
        "strengths": strengths,
        "thin_file_rescue": True,   # this is the signal for firms with no formal financials/bank account
        "note": ("Deterministic thin-file cash-flow signals from a mobile-money / POS-settlement "
                 "statement (arithmetic + keyword detection, no AI). Decision-support OVERLAY for "
                 "informal/no-file firms — NOT a component of the Imara Score."),
    }
