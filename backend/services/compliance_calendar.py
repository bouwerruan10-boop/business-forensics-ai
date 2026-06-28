"""
Statutory compliance calendar — DETERMINISTIC (no LLM).

The recurring spine of the accountant / tax-practitioner relationship: which
statutory obligations apply to THIS business, their cadence/timing, which are
FREE on-ramps most SMEs don't know about (EME B-BBEE affidavit, POPIA Information
Officer registration), and which are gaps/risks (compulsory VAT registration,
CIPC deregistration). Computed from intake Imara already captures — no new fields.

Turns a one-off report into a recurring, sticky utility. Decision-support /
awareness, not a legal determination; not an Imara Score input.
"""
import math
import re

_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]
VAT_THRESHOLD = 1_000_000
EME_CEILING = 10_000_000
QSE_CEILING = 50_000_000
SDL_PAYROLL_FLOOR = 500_000
_SDL_AVG_SALARY = 70_000   # rough per-head annual cost, to proxy the SDL payroll floor


def _n(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v if isinstance(v, (int, float))
                  else str(v).strip().replace(" ", "").replace(",", "").replace("R", ""))
    except (ValueError, TypeError):
        return None
    # reject non-finite (inf/nan) so a hostile figure can't crash int() downstream
    return f if math.isfinite(f) else None


def _year_end_month(tax_year_end: str):
    s = (tax_year_end or "").lower()
    for i, m in enumerate(_MONTHS):
        if m in s:
            return m.capitalize(), i + 1
    return None, None


def _it14_due(month_name):
    return ("~12 months after your {} year-end".format(month_name) if month_name
            else "12 months after your financial year-end")


def build_compliance_calendar(report) -> dict:
    """Return applicable statutory obligations with cadence + free on-ramps. Pure."""
    if not isinstance(report, dict):
        return {"available": False, "reason": "No report."}
    rev = _n(report.get("annual_revenue")) or _n((report.get("financial_figures") or {}).get("revenue")) or 0.0
    headcount = int(_n(report.get("headcount")) or 0)
    vat_reg = str(report.get("vat_registered") or "unknown").lower()
    entity = str(report.get("entity_type") or "").lower()
    cipc = str(report.get("cipc_number") or "").strip()
    tye = str(report.get("tax_year_end") or "")
    month_name, _m = _year_end_month(tye)
    is_company = ("pty" in entity or "ltd" in entity or "company" in entity or bool(re.match(r"^\s*\d{4}/", cipc)))

    # Need at least some identifying profile signal — don't fabricate a calendar from nothing.
    if rev <= 0 and headcount <= 0 and not is_company and vat_reg not in ("yes", "no", "true", "false", "registered"):
        return {"available": False, "reason": "Not enough profile data to build a compliance calendar."}

    obligations = []
    free_wins = []

    def add(title, authority, cadence, timing, action, priority, free=False, basis=""):
        item = {"title": title, "authority": authority, "cadence": cadence, "timing": timing,
                "action": action, "priority": priority, "free": free, "basis": basis}
        obligations.append(item)
        if free:
            free_wins.append({"title": title, "action": action})

    # ---- GAPS / RISKS first ----
    if vat_reg in ("no", "not", "false") and rev >= VAT_THRESHOLD:
        add("Compulsory VAT registration (overdue)", "SARS", "once (then VAT201 cycle)",
            "Register now — turnover exceeds R1m", "Register for VAT on eFiling; backdated liability + penalties accrue while unregistered.",
            "critical", basis="VAT Act 89/1991 s23 — compulsory once 12-month turnover exceeds R1,000,000.")
    if not cipc and is_company:
        add("Confirm CIPC registration & standing", "CIPC", "—",
            "Now", "No CIPC number on file — confirm the company is registered and not deregistered (a deregistered company cannot bank or contract).",
            "high", basis="Companies Act 71/2008.")

    # ---- CIPC annual return + beneficial ownership ----
    if is_company:
        add("CIPC annual return + beneficial-ownership register", "CIPC", "annual",
            "Each year on your incorporation anniversary",
            "File the annual return WITH the beneficial-ownership register (mandatory since 1 Jul 2024). Two missed years => deregistration (un-bankable).",
            "high", basis="Companies Act 71/2008 + CIPC 2024 beneficial-ownership rules.")

    # ---- Income tax + provisional ----
    if is_company:
        add("Company income tax return (ITR14/IT14)", "SARS", "annual",
            _it14_due(month_name), "Submit the company tax return for each year of assessment.",
            "medium", basis="Income Tax Act 58/1962.")
        add("Provisional tax (IRP6)", "SARS", "twice a year",
            ("6 months into the tax year and at your {} year-end".format(month_name) if month_name
             else "6 months into the tax year and at year-end"),
            "Estimate and pay provisional tax to avoid under-estimation penalties.",
            "medium", basis="Income Tax Act — 4th Schedule.")

    # ---- VAT201 ----
    if vat_reg in ("yes", "true", "registered"):
        add("VAT return (VAT201)", "SARS", "every 2 months (or monthly)",
            "By the 25th on eFiling after each VAT period",
            "File and pay VAT each period; keep input invoices to support claims.",
            "medium", basis="VAT Act 89/1991.")

    # ---- Payroll (employees) ----
    if headcount > 0:
        add("Payroll declaration (EMP201: PAYE/UIF/SDL)", "SARS", "monthly",
            "By the 7th of each month",
            "Declare and pay PAYE, UIF and SDL for your employees.", "medium",
            basis="Income Tax Act + UIF/SDL Acts.")
        add("Employer reconciliation (EMP501) + IRP5s", "SARS", "twice a year",
            "Interim ~September; annual ~May", "Reconcile payroll and issue IRP5/IT3(a) certificates.",
            "low", basis="SARS PAYE reconciliation.")
        payroll_proxy = headcount * _SDL_AVG_SALARY
        if payroll_proxy >= SDL_PAYROLL_FLOOR:
            add("Skills plan (WSP/ATR) — recover your SDL", "SETA", "annual",
                "By 30 April each year",
                "Submit the Workplace Skills Plan + Annual Training Report to recover up to 20% of your SDL as a mandatory grant — money you're entitled to back.",
                "low", basis="Skills Development Act — payroll above ~R500k attracts 1% SDL.")

    # ---- B-BBEE (free on-ramp for EME/QSE) ----
    if rev > 0 and rev < EME_CEILING:
        add("B-BBEE: free EME affidavit", "Commissioner of Oaths / dtic", "annual",
            "Renew yearly", "Get the FREE sworn EME affidavit (turnover < R10m) — auto Level 4, or Level 1 if >=51% black-owned. Improves tender/supply-chain access at zero cost.",
            "medium", free=True, basis="B-BBEE Act 53/2003 — Amended Codes (EME exemption).")
    elif rev and rev < QSE_CEILING:
        add("B-BBEE: QSE affidavit or verification", "Commissioner of Oaths / SANAS agency", "annual",
            "Renew yearly", "QSE (R10m-R50m): a sworn affidavit if >=51% black-owned (free), otherwise a SANAS verification certificate.",
            "low", basis="B-BBEE Act 53/2003 — Amended Codes (QSE).")
    elif rev >= QSE_CEILING:
        add("B-BBEE verification certificate", "SANAS-accredited agency", "annual",
            "Renew yearly", "Turnover above R50m requires a full B-BBEE verification certificate.",
            "low", basis="B-BBEE Act 53/2003 — Amended Codes.")

    # ---- POPIA Information Officer (free, applies to all) ----
    add("POPIA: register your Information Officer", "Information Regulator", "once (keep current)",
        "Now (free, ~30 min)",
        "Register your Information Officer with the Information Regulator — FREE; non-compliance risks fines up to R10m.",
        "medium", free=True, basis="POPIA Act 4/2013 s55.")

    if not obligations:
        return {"available": False, "reason": "Not enough profile data to build a compliance calendar."}

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    obligations.sort(key=lambda o: rank.get(o["priority"], 4))
    return {
        "available": True,
        "obligations": obligations,
        "free_quick_wins": free_wins,
        "count": len(obligations),
        "note": ("Your applicable SA statutory obligations — cadence, timing and the FREE on-ramps most SMEs "
                 "miss — computed from your profile (deterministic, no AI). A recurring checklist, not a legal "
                 "determination; confirm exact dates with your accountant/tax practitioner."),
    }
