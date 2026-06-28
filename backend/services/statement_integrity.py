"""
statement_integrity.py - deterministic bank-statement integrity checks.

Pure functions; the LLM only narrates. Two independent checks the strategic
research (2026-06-28) flagged as missing and high-value:

1. FORWARD BALANCE RECONCILIATION - the defining best practice for trusting a
   parsed statement: opening_balance + total_credits - total_debits must equal
   closing_balance. A mismatch means the parse dropped/duplicated rows OR the
   statement was tampered with. Honest by design: if the four summary figures
   are not all present, it reports "insufficient_data", never a fabricated pass.

2. PDF-METADATA FRAUD SIGNALS - a genuine bank statement is rendered by a banking
   system (Finacle, iText, Jasper, ...). A statement re-saved through a consumer
   PDF editor (Adobe Acrobat, iLovePDF, Word, Canva, ...) - especially with a
   modification date after its creation date - is a tamper signal worth a review.

These are RISK-AWARENESS flags, NOT accusations of fraud (same discipline as
services/tax_risk_flags.py). Decision-support, not a forensic determination.
"""

import io
import re

# Consumer / editing tools whose presence as the PDF producer or creator is a
# tamper signal on a document that should have come straight from a bank system.
_EDITING_TOOLS = (
    "adobe acrobat", "ilovepdf", "smallpdf", "pdfescape", "foxit", "nitro",
    "microsoft word", "word", "canva", "photoshop", "gimp", "libreoffice",
    "openoffice", "google docs", "pdf24", "sejda", "soda pdf", "pdffiller",
    "dochub", "wps office", "pages", "preview",
)
# Banking / reporting engines whose presence is REASSURING (lowers suspicion).
_BANK_ENGINES = (
    "finacle", "itext", "jasper", "birt", "oracle", "sap", "fpdf", "reportlab",
    "wkhtmltopdf", "prince", "crystal reports", "pdfbox", "ibm", "flexcube",
    "temenos", "t24", "datapdf", "openpdf", "pdfsharp",
)

_OPENING_LABELS = ("opening balance", "balance brought forward", "balance b/f",
                   "balance b/fwd", "opening bal", "previous balance", "balance forward")
_CLOSING_LABELS = ("closing balance", "balance carried forward", "balance c/f",
                   "balance c/fwd", "closing bal", "ending balance", "new balance")
_DEBIT_LABELS = ("total debits", "total payments", "total withdrawals", "total money out")
_CREDIT_LABELS = ("total credits", "total deposits", "total receipts", "total money in")

# A money token: optional R/-/(, digits with space/comma thousands, optional .dd or ,dd
_AMOUNT_RE = r"[-(]?\s*R?\s*([\d][\d  ,\.]*\d|\d)\s*\)?\s*(cr|dr)?"


def _to_float(raw, trailing=""):
    """Parse a SA-formatted money string to float (handles R, spaces, both decimal
    conventions, parentheses/Dr for negative)."""
    if raw is None:
        return None
    s = str(raw).strip()
    neg = s.startswith("(") or s.startswith("-") or (trailing or "").lower() == "dr"
    s = re.sub(r"[Rr()\s ]", "", s)
    if not s:
        return None
    # Decide decimal separator: if both '.' and ',' present, the LAST one is decimal.
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s:
        # comma is decimal only if it looks like ",dd" at the end; else thousands
        s = s.replace(",", ".") if re.search(r",\d{2}$", s) else s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if (neg and v > 0) else v


def _find_labelled_amount(text, labels):
    """Find the first money amount appearing on the same line as any of `labels`."""
    low = text.lower()
    for label in labels:
        idx = low.find(label)
        while idx != -1:
            line_end = low.find("\n", idx)
            segment = text[idx: line_end if line_end != -1 else idx + 120]
            m = re.search(_AMOUNT_RE, segment[len(label):])
            if m:
                val = _to_float(m.group(1), m.group(2))
                if val is not None:
                    return val
            idx = low.find(label, idx + 1)
    return None


def reconcile_balances(text, tolerance=1.0):
    """Forward balance reconciliation from statement text.

    Returns status: 'reconciled' | 'discrepancy' | 'insufficient_data'.
    """
    text = text if isinstance(text, str) else ""
    opening = _find_labelled_amount(text, _OPENING_LABELS)
    closing = _find_labelled_amount(text, _CLOSING_LABELS)
    debits = _find_labelled_amount(text, _DEBIT_LABELS)
    credits = _find_labelled_amount(text, _CREDIT_LABELS)

    found = {"opening_balance": opening, "closing_balance": closing,
             "total_debits": debits, "total_credits": credits}

    if None in (opening, closing, debits, credits):
        return {
            "status": "insufficient_data",
            "found": found,
            "note": ("Could not locate all four summary figures (opening, closing, total debits, total "
                     "credits) in the statement text, so no reconciliation was performed - this is NOT a "
                     "pass. Provide a clearer statement or a machine-readable feed to enable the check."),
        }

    expected_closing = opening + abs(credits) - abs(debits)
    diff = round(expected_closing - closing, 2)
    reconciled = abs(diff) <= max(tolerance, abs(closing) * 0.001)   # R1 or 0.1%, whichever larger
    return {
        "status": "reconciled" if reconciled else "discrepancy",
        "found": found,
        "expected_closing": round(expected_closing, 2),
        "actual_closing": round(closing, 2),
        "difference": diff,
        "note": ("opening + credits - debits ties to the closing balance." if reconciled else
                 "opening + credits - debits does NOT tie to the closing balance (R{:,.2f} out) - the parse "
                 "may have dropped/duplicated rows, or the statement figures are inconsistent. Review before "
                 "relying on these numbers.".format(abs(diff))),
    }


def _pdf_date(raw):
    """Parse a PDF date string like D:20240115093000+02'00' -> (yyyymmddHHMMSS int) or None."""
    if not raw:
        return None
    m = re.search(r"(\d{14})", str(raw))
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{8})", str(raw))
    return int(m.group(1) + "000000") if m else None


def check_pdf_metadata(pdf_bytes):
    """Inspect PDF metadata for tamper signals. Returns a risk band + flags."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            meta = dict(pdf.metadata or {})
    except Exception:
        return {"status": "unknown", "flags": [], "note": "Could not read PDF metadata."}

    producer = str(meta.get("Producer", "")).lower()
    creator = str(meta.get("Creator", "")).lower()
    blob = producer + " | " + creator
    flags = []

    editing = sorted({t for t in _EDITING_TOOLS if t in blob})
    bank_engine = sorted({t for t in _BANK_ENGINES if t in blob})
    if editing:
        flags.append("Produced/edited by a consumer PDF tool ({}) - a bank statement should come from a "
                     "banking system.".format(", ".join(editing)))

    created = _pdf_date(meta.get("CreationDate"))
    modified = _pdf_date(meta.get("ModDate"))
    edited_after = bool(created and modified and modified > created)
    if edited_after:
        flags.append("Modified after creation (ModDate later than CreationDate) - the file was changed "
                     "after it was first generated.")

    if editing and edited_after:
        status = "likely_tampered"
    elif editing or edited_after:
        status = "review"
    else:
        status = "clean"

    note = ("No tamper signals in the PDF metadata." if status == "clean"
            else "PDF metadata shows tamper signals - review the original statement.")
    if not meta:
        note = "PDF carries no metadata to verify (some banks strip it) - neutral, not a pass."
    return {
        "status": status,
        "flags": flags,
        "producer": meta.get("Producer", "") or "",
        "creator": meta.get("Creator", "") or "",
        "bank_engine_detected": bank_engine,
        "note": note,
    }


def assess_statement_integrity(pdf_bytes=None, text=""):
    """Combined integrity assessment: balance reconciliation + PDF-metadata signals."""
    recon = reconcile_balances(text)
    meta = check_pdf_metadata(pdf_bytes) if pdf_bytes else {"status": "unknown", "flags": [],
                                                            "note": "No PDF supplied for metadata check."}
    # overall risk: any hard signal -> elevated
    elevated = recon.get("status") == "discrepancy" or meta.get("status") == "likely_tampered"
    watch = meta.get("status") == "review" or recon.get("status") == "insufficient_data"
    overall = "elevated" if elevated else ("review" if watch else "clean")
    return {
        "as_of": "deterministic statement-integrity check",
        "overall": overall,
        "reconciliation": recon,
        "metadata": meta,
        "disclaimer": ("Risk-awareness only - not a forensic or fraud determination. A flag means 'verify "
                       "the original statement', not 'fraud'. Confirm anything material directly with the bank."),
    }
