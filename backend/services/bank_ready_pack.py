"""
Bank-Ready Pack — a deterministic, lender-facing PDF.

Research (r/PersonalFinanceZA "self employed bond frustrations"): SA banks ask
self-employed applicants for a specific bundle — signed financials + an
accountant's letter of total owner compensation incl. company-paid personal
expenses + an EBITDA/affordability view. This module assembles exactly that
bundle from fields Imara already computes deterministically (normalisation,
lender_view, bank_signals, financial_ratios) — no new AI, no invented numbers.

It is decision-support to help an owner get application-ready: NOT a credit
decision, NOT an Imara Score input, NOT financial advice (FAIS).
"""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

NAVY = colors.HexColor("#0b1f3a")
NAVY2 = colors.HexColor("#15396b")
GREY = colors.HexColor("#64748b")
LINE = colors.HexColor("#d9e0e8")
GOODC = colors.HexColor("#16a34a")
WARNC = colors.HexColor("#d97706")
CRITC = colors.HexColor("#dc2626")
_CELL = ParagraphStyle("brp_wrap", fontName="Helvetica", fontSize=9, leading=11,
                       textColor=colors.HexColor("#1f2933"))

_RealParagraph = Paragraph


def _para(text, style):
    """Self-healing Paragraph: retry XML-escaped if the parser chokes on raw <,>,&."""
    try:
        return _RealParagraph(text, style)
    except Exception:
        safe = (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        try:
            return _RealParagraph(safe, style)
        except Exception:
            return _RealParagraph("", style)


def _styles():
    ss = getSampleStyleSheet()
    out = {}
    out["title"] = ParagraphStyle("brp_title", parent=ss["Title"], textColor=colors.white,
                                  fontSize=22, leading=26, spaceAfter=2)
    out["sub"] = ParagraphStyle("brp_sub", parent=ss["Normal"], textColor=colors.HexColor("#c7d6ec"),
                                fontSize=9, leading=13)
    out["h"] = ParagraphStyle("brp_h", parent=ss["Heading2"], textColor=NAVY, fontSize=13,
                              leading=16, spaceBefore=14, spaceAfter=4)
    out["body"] = ParagraphStyle("brp_body", parent=ss["Normal"], fontSize=9.5, leading=14,
                                 textColor=colors.HexColor("#1f2933"))
    out["small"] = ParagraphStyle("brp_small", parent=ss["Normal"], fontSize=8, leading=11,
                                  textColor=GREY)
    out["cell"] = ParagraphStyle("brp_cell", parent=ss["Normal"], fontSize=9, leading=12)
    out["cellb"] = ParagraphStyle("brp_cellb", parent=ss["Normal"], fontSize=9, leading=12,
                                  textColor=colors.white)
    return out


def _money(n, cur="ZAR"):
    if n is None:
        return "—"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    return "%s %s%s" % (cur, "-" if n < 0 else "", "{:,.0f}".format(abs(n)))


def _d(x):
    """Coerce to dict (defensive — report subsections may be wrong-typed)."""
    return x if isinstance(x, dict) else {}


def _l(x):
    """Coerce to a list of dicts (drops non-dict items)."""
    return [i for i in x if isinstance(i, dict)] if isinstance(x, list) else []


def _table(rows, col_widths, header=True, st=None):
    rows = [[c if hasattr(c, "wrap") else _para(str(c), _CELL) for c in row] for row in rows]
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style + (st or [])))
    return t


def generate_bank_ready_pack(report: dict) -> bytes:
    report = report or {}
    g = report.get
    cur = g("currency", "ZAR") or "ZAR"
    figs = _d(g("financial_figures"))
    norm = _d(g("normalization"))
    lv = _d(g("lender_view"))
    bank = _d(g("bank_signals"))
    ratios = _d(g("financial_ratios"))
    S = _styles()
    M = lambda n: _money(n, cur)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            title="Bank-Ready Pack", author="Imara")
    story = []

    # ── Header band ──
    name = str(g("business_name") or "Your Business")
    head = Table([[_para("Bank-Ready Pack", S["title"])],
                  [_para(name + " &nbsp;·&nbsp; an application-readiness summary prepared by Imara", S["sub"])],
                  [_para("Decision-support to help you get finance-ready — not a credit decision, not financial advice.", S["sub"])]],
                 colWidths=[178 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                              ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                              ("LEFTPADDING", (0, 0), (-1, -1), 14),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                              ("TOPPADDING", (0, 0), (0, 0), 14),
                              ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
    story += [head, Spacer(1, 10)]

    # ── Business snapshot ──
    def idrow(k, v):
        return [_para(k, S["small"]), _para(str(v) if v not in (None, "", 0) else "—", S["cell"])]
    vatreg = g("vat_registered")
    vat = (g("vat_number") or ("Registered" if vatreg == "yes" else "Not registered" if vatreg == "no" else "—"))
    snap = [
        idrow("Entity type", g("entity_type")),
        idrow("Industry", g("industry")),
        idrow("Years in business", g("years_in_business")),
        idrow("VAT", vat),
        idrow("CIPC / reg. no.", g("cipc_number")),
        idrow("Banking partner", g("banking_partner")),
        idrow("Financial year-end", g("tax_year_end")),
        idrow("Annual revenue", M(figs.get("revenue") or g("annual_revenue"))),
    ]
    # two-column layout
    left = snap[:4]; right = snap[4:]
    grid = []
    for i in range(4):
        grid.append(left[i] + right[i])
    story += [_para("Business snapshot", S["h"]),
              _table(grid, [30 * mm, 59 * mm, 30 * mm, 59 * mm], header=False), Spacer(1, 4)]

    # ── Readiness one-liner ──
    if lv.get("available"):
        risk = lv.get("decline_risk", "")
        col = {"low": GOODC, "medium": WARNC, "high": CRITC}.get(risk, GREY)
        verdict_style = ParagraphStyle("v", parent=S["body"], textColor=col, fontSize=10.5, leading=14)
        story += [_para("<b>Lender readiness:</b> " + str(lv.get("verdict", "")) +
                        "  (cash-flow decline risk: <b>" + str(risk).upper() + "</b>)", verdict_style),
                  Spacer(1, 2)]

    # ── Section A: Normalised earnings ──
    story += [_para("1. True earning power — Adjusted EBITDA (deal/loan-book view)", S["h"])]
    if norm.get("available"):
        rows = [[_para("Measure", S["cellb"]), _para("Amount", S["cellb"])],
                ["Reported EBITDA (" + str(norm.get("ebitda_basis", "")).replace("_", " ") + ")", M(norm.get("reported_ebitda"))],
                ["Add-backs (conservative)", M(norm.get("add_backs_total_conservative"))],
                ["Add-backs (incl. owner-discretionary)", M(norm.get("add_backs_total_optimistic"))],
                [_para("<b>Adjusted EBITDA (indicative range)</b>", S["cell"]),
                 _para("<b>" + M(norm.get("adjusted_ebitda_low")) + " – " + M(norm.get("adjusted_ebitda_high")) + "</b>", S["cell"])]]
        story += [_table(rows, [120 * mm, 58 * mm])]
        adds = _l(norm.get("add_backs"))
        if adds:
            ab = [[_para("Add-back", S["cellb"]), _para("Amount", S["cellb"]), _para("Basis", S["cellb"])]]
            for a in adds:
                ab.append([a.get("label", ""), M(a.get("amount")), a.get("note", "")])
            story += [Spacer(1, 5), _para("Owner-compensation &amp; non-recurring add-backs (the accountant's-letter items)", S["body"]),
                      _table(ab, [58 * mm, 30 * mm, 90 * mm])]
            story += [Spacer(1, 4), _para(
                "On the basis above, the company-paid owner/personal and one-off costs are added back to reflect the "
                "business's true earning power. The owner-personal portion should be confirmed by the owner/accountant "
                "for the bank's file.", S["small"])]
        lf = _d(norm.get("loan_account_flag"))
        if lf.get("flagged"):
            story += [Spacer(1, 4), _para("<b>Note:</b> " + str(lf.get("detail", "")) + " <b>Action:</b> " + str(lf.get("fix", "")), S["small"])]
    else:
        story += [_para(norm.get("reason", "Adjusted-earnings view not available — provide an income statement."), S["small"])]

    # ── Section B: Bank conduct + reconciliation ──
    story += [_para("2. Cash-flow &amp; bank-conduct evidence", S["h"])]
    m = _d(lv.get("cash_flow_metrics"))
    if bank.get("available") or m.get("available"):
        rows = [[_para("Signal", S["cellb"]), _para("Value", S["cellb"])],
                ["Months of statement history", m.get("period_months") or bank.get("period_months") or "—"],
                ["Average balance", M(m.get("average_daily_balance") or bank.get("avg_balance"))],
                ["Average monthly deposits", M(m.get("average_monthly_deposits"))],
                ["Deposit consistency", (m.get("deposit_consistency") or bank.get("deposit_consistency") or "—")],
                ["Returned / bounced debit orders", m.get("returned_debit_orders") if m.get("returned_debit_orders") is not None else bank.get("returned_debit_orders", "—")],
                ["Lowest balance in period", M(m.get("min_balance") if m.get("min_balance") is not None else bank.get("min_balance"))]]
        story += [_table(rows, [120 * mm, 58 * mm])]
        rec = _d(lv.get("reconciliation"))
        if rec.get("available"):
            story += [Spacer(1, 5), _para("Bank deposits vs declared revenue", S["body"]),
                      _table([[_para("Declared revenue", S["cellb"]), _para("Annualised deposits", S["cellb"]), _para("Gap", S["cellb"])],
                              [M(rec.get("declared_revenue")), M(rec.get("annualized_deposits")),
                               (str(rec.get("gap_pct")) + "%" if rec.get("gap_pct") is not None else "—")]],
                             [60 * mm, 60 * mm, 58 * mm]),
                      Spacer(1, 3), _para(rec.get("interpretation", ""), S["small"])]
    else:
        story += [_para("No usable bank statement was provided. Lenders weight 3–6 months of bank conduct heavily — "
                        "attach business bank statements to strengthen the application.", S["small"])]

    # ── Section C: Affordability ──
    bc = _d(lv.get("borrowing_capacity"))
    if bc.get("working_capital_facility") or bc.get("term_loan"):
        story += [_para("3. Indicative affordability / debt-service capacity", S["h"])]
        wc = _d(bc.get("working_capital_facility"))
        tl = _d(bc.get("term_loan"))
        rows = [[_para("Facility", S["cellb"]), _para("Indicative range", S["cellb"]), _para("Basis", S["cellb"])]]
        if wc:
            rows.append(["Working-capital facility", M(wc.get("low")) + " – " + M(wc.get("high")), wc.get("basis", "")])
        if tl:
            rows.append(["Term loan (principal)", M(tl.get("implied_principal_low")) + " – " + M(tl.get("implied_principal_high")), tl.get("basis", "")])
            rows.append(["Supportable annual debt service", M(tl.get("supportable_annual_debt_service_low")) + " – " + M(tl.get("supportable_annual_debt_service_high")), "Adjusted EBITDA ÷ DSCR"])
        story += [_table(rows, [52 * mm, 58 * mm, 68 * mm]),
                  Spacer(1, 3), _para(bc.get("assumptions", ""), S["small"])]

    # ── Section D: Key ratios ──
    if isinstance(ratios, dict) and ratios:
        story += [_para("4. Key financial ratios", S["h"])]
        rr = [[_para("Ratio", S["cellb"]), _para("Value", S["cellb"]), _para("Sector benchmark", S["cellb"]), _para("Status", S["cellb"])]]
        for v in ratios.values():
            if not isinstance(v, dict):
                continue
            val = v.get("value")
            unit = v.get("unit", "")
            valstr = (("%s %s" % (val, unit)) if unit not in ("%", "x", "") else ("%s%s" % (val, unit))) if val is not None else "—"
            bm = v.get("benchmark")
            bmstr = (("%s %s" % (bm, unit)) if unit not in ("%", "x", "") else ("%s%s" % (bm, unit))) if bm is not None else "—"
            rr.append([v.get("label", ""), valstr, bmstr, str(v.get("status", "")).title()])
        if len(rr) > 1:
            story += [_table(rr, [60 * mm, 38 * mm, 44 * mm, 36 * mm])]

    # ── Section E: Readiness fixes ──
    reasons = _l(lv.get("reasons"))
    if reasons:
        story += [_para("5. What to strengthen before you apply", S["h"])]
        fr = [[_para("Issue", S["cellb"]), _para("Fix", S["cellb"])]]
        for r in reasons:
            fr.append([r.get("issue", ""), r.get("fix", "")])
        story += [_table(fr, [82 * mm, 96 * mm])]

    # ── Disclaimer ──
    story += [Spacer(1, 10), HRFlowable(width="100%", color=LINE, thickness=0.5), Spacer(1, 4)]
    ds = report.get("decision_support") or {}
    disclaimer = ds.get("summary") if isinstance(ds, dict) else None
    story += [_para(
        (disclaimer or "") + "  This pack is indicative decision-support prepared from the business's own documents to "
        "help it become finance-ready. It is not a credit decision, not a creditworthiness determination, and not "
        "financial advice. Every figure is computed deterministically from the supplied financials and bank statements.",
        S["small"])]

    doc.build(story)
    return buf.getvalue()
