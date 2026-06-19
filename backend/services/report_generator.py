"""
Premium PDF Report Generator — Imara
McKinsey-quality layout: dark cover, SCR narrative, benchmark callouts,
colour-coded finding cards, 90-day roadmap, quick wins panel.
"""
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from services.charts import score_bar_chart, severity_donut, roadmap_timeline

# ── Palette ──────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0D1B2A")
NAVY_MID  = colors.HexColor("#14263A")
NAVY_LITE = colors.HexColor("#1E3250")
GOLD      = colors.HexColor("#C9A84C")
GOLD_LITE = colors.HexColor("#E8C97A")
WHITE     = colors.white
OFF_WHITE = colors.HexColor("#F8F7F4")
LIGHT_GRAY = colors.HexColor("#EBEBEB")
MID_GRAY  = colors.HexColor("#888888")
DARK_GRAY = colors.HexColor("#555555")

RED      = colors.HexColor("#C0392B")
RED_BG   = colors.HexColor("#FDECEA")
ORANGE   = colors.HexColor("#D35400")
ORANGE_BG = colors.HexColor("#FEF0E6")
AMBER    = colors.HexColor("#C9820A")
AMBER_BG = colors.HexColor("#FEF8E6")
GREEN    = colors.HexColor("#1A7A40")
GREEN_BG = colors.HexColor("#E8F5EE")

SEV_COLOR  = {"critical": RED,    "high": ORANGE,  "medium": AMBER,  "low": GREEN}
SEV_BG     = {"critical": RED_BG, "high": ORANGE_BG, "medium": AMBER_BG, "low": GREEN_BG}
SEV_LABEL  = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm
CONTENT_W = PAGE_W - 2 * MARGIN


# ── Entry point ───────────────────────────────────────────────────

def generate_pdf_report(report: dict, audience: str = "owner") -> bytes:
    """
    Generate a premium PDF report.
    audience: "owner"   — plain-language, action-focused, full findings
              "banker"  — credit/risk focus, ratios, fraud indicator
              "investor"— valuation, growth story, strategy findings
    """
    audience = audience.lower() if audience else "owner"

    buffer = io.BytesIO()
    biz_name = report.get("business_name", "Business")
    title_map = {
        "owner":    f"{biz_name} — Business Health Report",
        "banker":   f"{biz_name} — Credit Assessment Report",
        "investor": f"{biz_name} — Investment Analysis Report",
    }

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title=title_map.get(audience, f"{biz_name} — Forensics Report"),
        author="Imara",
    )

    story = []

    # ── Cover (audience-specific) ──────────────────────────────────
    if audience == "banker":
        _cover_page_banker(story, report)
    elif audience == "investor":
        _cover_page_investor(story, report)
    else:
        _cover_page(story, report)

    story.append(PageBreak())

    # ── Imara Score hero (all audiences) ──────────
    _imara_score_block(story, report)

    # ── Traffic light scorecard (all audiences) ────────────────────
    _traffic_light_section(story, report)
    _financial_ratios_section(story, report)
    story.append(PageBreak())

    # ── Standard narrative sections ────────────────────────────────
    _toc_section(story, report)
    story.append(PageBreak())
    _executive_summary_section(story, report)
    story.append(PageBreak())
    _situation_section(story, report)
    _quick_wins_section(story, report)
    story.append(PageBreak())

    # ── Audience-filtered findings ─────────────────────────────────
    _department_findings_section(story, report, audience=audience)
    story.append(PageBreak())

    # ── Credit readiness section (owner + banker) ──────────────────
    if audience in ("owner", "banker"):
        _credit_readiness_section(story, report)
        story.append(PageBreak())

    # ── Valuation section (owner + investor) ──────────────────────
    if audience in ("owner", "investor"):
        _valuation_section(story, report)
        story.append(PageBreak())

    # ── Fraud risk section (banker + investor) ─────────────────────
    if audience in ("banker", "investor"):
        _fraud_risk_section(story, report)
        story.append(PageBreak())

    # ── Roadmap + closing ─────────────────────────────────────────
    _roadmap_section(story, report)
    _closing_section(story, report)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


# ── Page callbacks ────────────────────────────────────────────────

def _footer(canvas, doc):
    """Page number footer — skipped on cover page."""
    canvas.saveState()
    page_num = doc.page
    if page_num == 1:
        canvas.restoreState()
        return
    biz = doc.title or "Imara"
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(MARGIN, 0.9 * cm, "CONFIDENTIAL — For management use only")
    canvas.drawRightString(PAGE_W - MARGIN, 0.9 * cm, f"Page {page_num - 1}")
    # thin rule above footer
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 1.1 * cm, PAGE_W - MARGIN, 1.1 * cm)
    canvas.restoreState()


# ── Cover page ────────────────────────────────────────────────────

def _cover_page(story, report):
    biz     = report.get("business_name", "Business")
    industry = report.get("industry", "General Business")
    cur     = report.get("currency", "ZAR")
    rev     = report.get("annual_revenue", 0)
    country = report.get("country", "")
    today   = date.today().strftime("%d %B %Y")
    scores  = report.get("scores", {})
    health  = scores.get("business_health", 0)
    findings_total = report.get("total_findings", 0)
    critical = report.get("critical_findings", 0)
    high     = report.get("high_findings", 0)

    # ── Top header band ──
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "BUSINESS FORENSICS AI",
        _style(fontSize=9, fontName="Helvetica-Bold", textColor=GOLD,
               letterSpacing=2.5, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 2 * cm))

    # ── Report label ──
    story.append(Paragraph(
        "FORENSIC BUSINESS ANALYSIS",
        _style(fontSize=9, fontName="Helvetica", textColor=MID_GRAY,
               letterSpacing=3, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.5 * cm))

    # ── Client name ──
    story.append(Paragraph(
        biz,
        _style(fontSize=36, fontName="Helvetica-Bold", textColor=NAVY,
               leading=40, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"{industry}  ·  {country}  ·  {today}" if country else f"{industry}  ·  {today}",
        _style(fontSize=10, textColor=DARK_GRAY, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 2 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 1.5 * cm))

    # ── Key metrics panel ──
    rev_str = f"{cur} {rev:,.0f}" if rev else "—"
    metric_data = [
        ["ANNUAL REVENUE", "HEALTH SCORE", "FINDINGS", "CRITICAL"],
        [rev_str, f"{health}/100", str(findings_total), str(critical)],
    ]
    col_w = CONTENT_W / 4
    tbl = Table(metric_data, colWidths=[col_w] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("LETTERSPACING", (0, 0), (-1, 0), 1),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), OFF_WHITE),
        # Colour the critical cell
        ("TEXTCOLOR", (3, 1), (3, 1), RED if critical > 0 else GREEN),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3 * cm))

    # ── Confidentiality notice ──
    story.append(Paragraph(
        "STRICTLY CONFIDENTIAL",
        _style(fontSize=8, fontName="Helvetica-Bold", textColor=DARK_GRAY,
               letterSpacing=1.5, alignment=TA_LEFT)
    ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "This report has been prepared exclusively for the management of the above-named entity. "
        "It contains sensitive financial and operational findings derived from proprietary business data. "
        "Distribution, reproduction, or disclosure to any third party without prior written consent is prohibited.",
        _style(fontSize=7.5, textColor=MID_GRAY, leading=11, alignment=TA_JUSTIFY)
    ))


# ── Table of Contents ────────────────────────────────────────────

def _toc_section(story, report):
    _section_header(story, "CONTENTS")

    sections = [
        ("1", "Situation Overview"),
        ("2", "Executive Summary"),
        ("3", "Quick Wins (< 30 Days)"),
        ("4", "Department Findings"),
        ("5", "90-Day Implementation Roadmap"),
    ]
    for num, title in sections:
        row = Table(
            [[
                Paragraph(f"{num}.", _style(fontSize=10, fontName="Helvetica-Bold", textColor=GOLD)),
                Paragraph(title, _style(fontSize=10, textColor=NAVY)),
            ]],
            colWidths=[0.7 * cm, CONTENT_W - 0.7 * cm],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, LIGHT_GRAY),
        ]))
        story.append(row)


# ── Situation Overview ────────────────────────────────────────────

def _situation_section(story, report):
    _section_header(story, "SITUATION OVERVIEW")

    situation   = report.get("situation", "")
    complication = report.get("complication", "")
    resolution  = report.get("resolution", "")
    biz_summary = report.get("business_model_summary", "")

    if biz_summary:
        _callout_box(story, "Business Model", biz_summary, NAVY_LITE, GOLD)
        story.append(Spacer(1, 0.4 * cm))

    scr_data = [
        [_scr_label("SITUATION"), _scr_label("COMPLICATION"), _scr_label("RESOLUTION")],
        [
            Paragraph(situation or "—", _style(fontSize=9, leading=13, textColor=DARK_GRAY)),
            Paragraph(complication or "—", _style(fontSize=9, leading=13, textColor=DARK_GRAY)),
            Paragraph(resolution or "—", _style(fontSize=9, leading=13, textColor=DARK_GRAY)),
        ],
    ]
    scr_w = CONTENT_W / 3
    scr = Table(scr_data, colWidths=[scr_w] * 3)
    scr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, 1), OFF_WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(scr)

    # Key risks / opportunities
    risks = report.get("key_risks", [])
    opps  = report.get("key_opportunities", [])
    if risks or opps:
        story.append(Spacer(1, 0.5 * cm))
        ro_data = []
        if risks:
            ro_data.append([
                Paragraph("KEY RISKS", _style(fontSize=8, fontName="Helvetica-Bold",
                           textColor=RED, letterSpacing=1)),
                Paragraph("KEY OPPORTUNITIES", _style(fontSize=8, fontName="Helvetica-Bold",
                           textColor=GREEN, letterSpacing=1)),
            ])
            risk_text = "\n".join(f"• {r}" for r in risks[:4])
            opp_text  = "\n".join(f"• {o}" for o in opps[:4])
            ro_data.append([
                Paragraph(risk_text, _style(fontSize=9, leading=13, textColor=DARK_GRAY)),
                Paragraph(opp_text,  _style(fontSize=9, leading=13, textColor=DARK_GRAY)),
            ])
        ro_tbl = Table(ro_data, colWidths=[CONTENT_W / 2] * 2)
        ro_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, LIGHT_GRAY),
        ]))
        story.append(ro_tbl)


# ── Executive Summary ─────────────────────────────────────────────

def _executive_summary_section(story, report):
    _section_header(story, "EXECUTIVE SUMMARY")

    # Score cards
    scores = report.get("scores", {})
    score_items = [
        ("Business Health", scores.get("business_health", 0), "Overall score"),
        ("Profitability",   scores.get("profitability", 0),   "Financial health"),
        ("Efficiency",      scores.get("efficiency", 0),      "Operations & HR"),
        ("Risk",            scores.get("risk", 0),            "Audit & legal"),
    ]
    score_data = [
        [Paragraph(s[0], _style(fontSize=8, fontName="Helvetica-Bold", textColor=WHITE,
                                alignment=TA_CENTER))
         for s in score_items],
        [_score_cell(s[1], s[2]) for s in score_items],
    ]
    col_w = CONTENT_W / 4
    stbl = Table(score_data, colWidths=[col_w] * 4)
    stbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(stbl)
    story.append(Spacer(1, 0.5 * cm))

    # Findings tally
    tally_data = [
        ["TOTAL FINDINGS", "CRITICAL", "HIGH PRIORITY", "QUICK WINS"],
        [
            str(report.get("total_findings", 0)),
            str(report.get("critical_findings", 0)),
            str(report.get("high_findings", 0)),
            str(len(report.get("quick_wins", []))),
        ],
    ]
    col_w3 = CONTENT_W / 4
    ttbl = Table(tally_data, colWidths=[col_w3] * 4)
    ttbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), OFF_WHITE),
        ("TEXTCOLOR", (0, 0), (-1, 0), DARK_GRAY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("LETTERSPACING", (0, 0), (-1, 0), 1),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 22),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
        ("TEXTCOLOR", (1, 1), (1, 1), RED),
        ("TEXTCOLOR", (2, 1), (2, 1), ORANGE),
        ("TEXTCOLOR", (3, 1), (3, 1), GREEN),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(ttbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── Chart row: score bars + severity donut ───────────────────
    try:
        scores_for_chart = {}
        for key in ("business_health_score", "profitability_score",
                    "efficiency_score", "risk_score"):
            scores_for_chart[key] = (
                scores.get(key)
                or scores.get(key.replace("_score", ""))
                or report.get(key, 0)
            )
        bar_png  = score_bar_chart(scores_for_chart, width=5.2, height=2.4)
        donut_png = severity_donut(_collect_all_findings(report), width=3.2)

        bar_img   = Image(io.BytesIO(bar_png),  width=9.5 * cm, height=4.4 * cm)
        donut_img = Image(io.BytesIO(donut_png), width=5.5 * cm, height=4.4 * cm)

        chart_tbl = Table(
            [[bar_img, donut_img]],
            colWidths=[9.8 * cm, 5.8 * cm],
        )
        chart_tbl.setStyle(TableStyle([
            ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(chart_tbl)
        story.append(Spacer(1, 0.4 * cm))
    except Exception:
        pass  # charts are nice-to-have; never break the PDF

    # Executive summary narrative
    summary = report.get("executive_summary") or report.get("summary", "")
    for para in summary.split("\n\n"):
        if para.strip():
            story.append(Paragraph(
                para.strip(),
                _style(fontSize=9.5, leading=15, textColor=DARK_GRAY, alignment=TA_JUSTIFY)
            ))
            story.append(Spacer(1, 0.25 * cm))

    # Top 5 priority issues
    top_issues = report.get("top_priority_issues", [])
    if top_issues:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "PRIORITY ISSUES",
            _style(fontSize=8, fontName="Helvetica-Bold", textColor=NAVY, letterSpacing=1.5)
        ))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY))
        story.append(Spacer(1, 0.15 * cm))

        for issue in top_issues[:5]:
            rank = issue.get("rank", "")
            title = issue.get("title", "")
            impact = issue.get("estimated_total_impact", "")
            why = issue.get("why_critical", "")
            is_qw = issue.get("quick_win", False)

            row = Table(
                [[
                    Paragraph(
                        f'<font color="#C9A84C">#{rank}</font>',
                        _style(fontSize=11, fontName="Helvetica-Bold", alignment=TA_CENTER)
                    ),
                    _issue_cell(title, why, impact, is_qw),
                ]],
                colWidths=[1.0 * cm, CONTENT_W - 1.0 * cm],
            )
            row.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, LIGHT_GRAY),
            ]))
            story.append(row)


# ── Quick Wins ────────────────────────────────────────────────────

def _quick_wins_section(story, report):
    quick_wins = report.get("quick_wins", [])
    if not quick_wins:
        return

    story.append(Spacer(1, 0.5 * cm))
    _section_header(story, "QUICK WINS  (< 30 DAYS)")

    narrative = report.get("quick_wins_narrative", "")
    if narrative:
        _callout_box(story, "Quick Win Summary", narrative, GREEN_BG, GREEN)
        story.append(Spacer(1, 0.3 * cm))

    for f in quick_wins[:8]:
        sev = f.get("severity", "medium")
        _finding_card(story, f, sev)


# ── Department Findings ───────────────────────────────────────────

def _department_findings_section(story, report, audience: str = "owner"):
    _section_header(story, "DEPARTMENT FINDINGS")

    dept = report.get("department_findings", {})
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    # Audience-specific agent filter
    if audience == "banker":
        _include = {
            "Financial Agent", "Accounting Agent", "Auditor Agent",
            "Legal Risk Agent", "Fraud & Anomaly Detection Agent", "Credit Readiness Agent",
        }
    elif audience == "investor":
        _include = {
            "Financial Agent", "Strategy Agent", "Marketing Agent",
            "Sales Agent", "HR Agent", "Operations Agent",
            "Valuation Agent", "Forecast Agent",
        }
    else:
        _include = None  # owner: all agents

    for agent_name, findings in dept.items():
        if not findings:
            continue
        if _include and agent_name not in _include:
            continue

        # Agent sub-header
        story.append(Spacer(1, 0.5 * cm))
        story.append(KeepTogether([
            Paragraph(
                agent_name.upper(),
                _style(fontSize=10, fontName="Helvetica-Bold", textColor=GOLD)
            ),
            HRFlowable(width="100%", thickness=1, color=GOLD),
            Spacer(1, 0.1 * cm),
        ]))

        sorted_findings = sorted(findings, key=lambda f: sev_order.get(f.get("severity", "medium"), 9))
        for f in sorted_findings:
            _finding_card(story, f, f.get("severity", "medium"))


# ── Finding card ─────────────────────────────────────────────────

def _finding_card(story, f: dict, severity: str):
    sev     = severity
    sc      = SEV_COLOR.get(sev, MID_GRAY)
    bg      = SEV_BG.get(sev, OFF_WHITE)
    label   = SEV_LABEL.get(sev, sev.upper())
    title   = f.get("title", "")
    detail  = f.get("detail", "")
    impact  = f.get("financial_impact", "")
    rec     = f.get("recommendation", "")
    roi     = f.get("roi_estimate", "")
    bench   = f.get("benchmark_reference", "")
    coi     = f.get("cost_of_inaction", "")
    qw      = f.get("quick_win", False)
    source  = f.get("data_source", "")

    inner = []

    # Title row
    title_row = Table(
        [[
            Paragraph(label, _style(fontSize=7, fontName="Helvetica-Bold",
                                    textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(
                f'{"⚡ " if qw else ""}{title}',
                _style(fontSize=10, fontName="Helvetica-Bold", textColor=NAVY)
            ),
        ]],
        colWidths=[1.5 * cm, CONTENT_W - 1.5 * cm],
    )
    title_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), sc),
        ("BACKGROUND", (1, 0), (1, 0), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
    ]))
    inner.append(title_row)

    # Detail
    if detail:
        inner.append(Spacer(1, 0.1 * cm))
        inner.append(Paragraph(
            detail,
            _style(fontSize=8.5, leading=13, textColor=DARK_GRAY, alignment=TA_JUSTIFY)
        ))

    # Benchmark row
    if bench:
        inner.append(Spacer(1, 0.1 * cm))
        inner.append(Paragraph(
            f"📊  {bench}",
            _style(fontSize=8, textColor=MID_GRAY, leading=11)
        ))

    # Metrics row
    metrics = []
    if impact:
        metrics.append(f"💰  Financial impact: <b>{impact}</b>")
    if coi:
        metrics.append(f"⚠️  Cost of inaction: {coi}")
    if roi:
        metrics.append(f"📈  ROI: {roi}")
    if source:
        metrics.append(f"📋  Source: {source}")

    if metrics:
        inner.append(Spacer(1, 0.1 * cm))
        for m in metrics:
            inner.append(Paragraph(
                m,
                _style(fontSize=8, leading=12, textColor=DARK_GRAY)
            ))

    # Recommendation
    if rec:
        inner.append(Spacer(1, 0.1 * cm))
        inner.append(Paragraph(
            f"→  {rec}",
            _style(fontSize=8.5, fontName="Helvetica-Bold", textColor=GREEN, leading=12)
        ))

    inner.append(Spacer(1, 0.15 * cm))

    card = Table(
        [[_wrap_flowables(inner)]],
        colWidths=[CONTENT_W],
    )
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, sc),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(Spacer(1, 0.25 * cm))
    story.append(KeepTogether([card]))


# ── Banker cover page ─────────────────────────────────────────────

def _cover_page_banker(story, report):
    biz      = report.get("business_name", "Business")
    industry = report.get("industry", "General Business")
    cur      = report.get("currency", "ZAR")
    rev      = report.get("annual_revenue", 0)
    country  = report.get("country", "")
    today    = date.today().strftime("%d %B %Y")
    credit_score = report.get("credit_score", 0)
    credit_grade = report.get("credit_grade", "—")
    fraud_risk   = report.get("fraud_risk_level", "unknown").upper()

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "BUSINESS FORENSICS AI  ·  CREDIT ASSESSMENT",
        _style(fontSize=9, fontName="Helvetica-Bold", textColor=GOLD, letterSpacing=2.5)
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(
        "CREDIT ASSESSMENT REPORT",
        _style(fontSize=9, fontName="Helvetica", textColor=MID_GRAY, letterSpacing=3)
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        biz,
        _style(fontSize=36, fontName="Helvetica-Bold", textColor=NAVY, leading=40)
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"{industry}  ·  {country}  ·  {today}" if country else f"{industry}  ·  {today}",
        _style(fontSize=10, textColor=DARK_GRAY)
    ))
    story.append(Spacer(1, 2 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 1.5 * cm))

    # Grade prominently
    grade_color = {
        "A": GREEN, "B": colors.HexColor("#1A7A40"),
        "C": AMBER,  "D": ORANGE, "F": RED,
    }.get(credit_grade, MID_GRAY)

    fraud_color = {"low": GREEN, "medium": AMBER, "high": ORANGE, "critical": RED}.get(
        report.get("fraud_risk_level", "unknown"), MID_GRAY
    )
    rev_str = f"{cur} {rev:,.0f}" if rev else "—"

    metric_data = [
        ["CREDIT GRADE", "CREDIT SCORE", "FRAUD RISK", "ANNUAL REVENUE"],
        [credit_grade or "—", f"{credit_score}/100", fraud_risk, rev_str],
    ]
    col_w = CONTENT_W / 4
    tbl = Table(metric_data, colWidths=[col_w] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("TEXTCOLOR", (0, 1), (0, 1), grade_color),
        ("TEXTCOLOR", (1, 1), (1, 1), grade_color),
        ("TEXTCOLOR", (2, 1), (2, 1), fraud_color),
        ("TEXTCOLOR", (3, 1), (3, 1), NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), OFF_WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        "PREPARED FOR CREDIT / LENDING INSTITUTION — STRICTLY CONFIDENTIAL",
        _style(fontSize=8, fontName="Helvetica-Bold", textColor=DARK_GRAY, letterSpacing=1)
    ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "This credit assessment has been generated by Imara for use by authorised "
        "financial institutions in evaluating lending or facility applications. It does not constitute "
        "a formal credit opinion and must be used in conjunction with your institution's own due diligence.",
        _style(fontSize=7.5, textColor=MID_GRAY, leading=11, alignment=TA_JUSTIFY)
    ))


# ── Investor cover page ────────────────────────────────────────────

def _cover_page_investor(story, report):
    biz      = report.get("business_name", "Business")
    industry = report.get("industry", "General Business")
    cur      = report.get("currency", "ZAR")
    rev      = report.get("annual_revenue", 0)
    country  = report.get("country", "")
    today    = date.today().strftime("%d %B %Y")
    val_low  = report.get("valuation_low", 0)
    val_high = report.get("valuation_high", 0)
    val_mid  = report.get("valuation_mid", 0)
    multiple = report.get("valuation_ebitda_multiple", 0)
    scores   = report.get("scores", {})
    health   = scores.get("business_health", 0)

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "BUSINESS FORENSICS AI  ·  INVESTMENT ANALYSIS",
        _style(fontSize=9, fontName="Helvetica-Bold", textColor=GOLD, letterSpacing=2.5)
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(
        "INVESTMENT ANALYSIS REPORT",
        _style(fontSize=9, fontName="Helvetica", textColor=MID_GRAY, letterSpacing=3)
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        biz,
        _style(fontSize=36, fontName="Helvetica-Bold", textColor=NAVY, leading=40)
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"{industry}  ·  {country}  ·  {today}" if country else f"{industry}  ·  {today}",
        _style(fontSize=10, textColor=DARK_GRAY)
    ))
    story.append(Spacer(1, 2 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 1.5 * cm))

    val_range = (f"{cur} {val_low:,.0f} – {cur} {val_high:,.0f}" if val_low else "—")
    val_mid_str = f"{cur} {val_mid:,.0f}" if val_mid else "—"
    mult_str = f"{multiple:.1f}×" if multiple else "—"
    rev_str  = f"{cur} {rev:,.0f}" if rev else "—"

    metric_data = [
        ["VALUATION RANGE", "MID-POINT", "EBITDA MULTIPLE", "HEALTH SCORE"],
        [val_range, val_mid_str, mult_str, f"{health}/100"],
    ]
    col_w = CONTENT_W / 4
    tbl = Table(metric_data, colWidths=[col_w] * 4)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), OFF_WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        "PREPARED FOR INVESTOR / ACQUIRER — STRICTLY CONFIDENTIAL",
        _style(fontSize=8, fontName="Helvetica-Bold", textColor=DARK_GRAY, letterSpacing=1)
    ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        "This investment analysis has been generated by Imara. Valuations are "
        "indicative estimates based on AI-derived financial data and industry benchmarks. They do "
        "not constitute a formal valuation opinion. Engage a qualified valuator or M&A advisor "
        "before transacting.",
        _style(fontSize=7.5, textColor=MID_GRAY, leading=11, alignment=TA_JUSTIFY)
    ))


# ── Shared helper utilities ───────────────────────────────────────


def _scr_label(text: str):
    """Return a centred, GOLD-tinted header paragraph for SCR table headers."""
    return Paragraph(
        text,
        _style(fontSize=8, fontName="Helvetica-Bold", textColor=GOLD_LITE,
               alignment=TA_CENTER, letterSpacing=1)
    )


def _score_cell(score: int, subtitle: str):
    """Return a coloured score + subtitle paragraph for score-card tables."""
    if score >= 70:
        col = GREEN
    elif score >= 40:
        col = AMBER
    else:
        col = RED
    lines = (
        f'<font name="Helvetica-Bold" size="18" color="#{_hex(col)}">{score}</font><br/>'
        f'<font name="Helvetica" size="7" color="#{_hex(MID_GRAY)}">{subtitle}</font>'
    )
    return Paragraph(lines, _style(alignment=TA_CENTER, leading=14))


def _style(**kwargs):
    """Create a one-off ParagraphStyle from keyword args."""
    char_space = kwargs.pop("letterSpacing", 0)
    ps = ParagraphStyle(
        name="_auto",
        fontName=kwargs.pop("fontName", "Helvetica"),
        fontSize=kwargs.pop("fontSize", 10),
        textColor=kwargs.pop("textColor", colors.black),
        alignment=kwargs.pop("alignment", TA_LEFT),
        charSpace=char_space,
        **kwargs,
    )
    return ps


def _section_header(story, title: str):
    """Gold underlined section header."""
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        title,
        ParagraphStyle("_sh", fontName="Helvetica-Bold", fontSize=8,
                       textColor=GOLD, charSpace=2, spaceBefore=0)
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 0.3 * cm))


def _hex(c) -> str:
    """Return uppercase 6-char hex string (no #) from a ReportLab color."""
    return "%02X%02X%02X" % (int(c.red * 255), int(c.green * 255), int(c.blue * 255))


def _wrap_flowables(flowables):
    """Wrap a list of flowables so it can be placed inside a single table cell.
    ReportLab table cells accept a list of flowables directly, so we return the
    list as-is (filtering out any None entries for safety)."""
    if flowables is None:
        return []
    if not isinstance(flowables, (list, tuple)):
        return [flowables]
    return [fl for fl in flowables if fl is not None]


def _imara_band_colors(score):
    if score >= 80:
        return GOLD, colors.HexColor("#FBF4DE")
    if score >= 65:
        return GREEN, GREEN_BG
    if score >= 50:
        return AMBER, AMBER_BG
    if score >= 35:
        return ORANGE, ORANGE_BG
    return RED, RED_BG


def _imara_score_block(story, report):
    """Imara Score hero — composite score, band, and component breakdown."""
    score = report.get("imara_score")
    if score is None:
        return
    band  = report.get("imara_band", "")
    label = report.get("imara_label", "")
    components = report.get("imara_components", []) or []
    col, bg = _imara_band_colors(score)
    canon = report.get("imara_color")
    if canon:
        try:
            col = colors.HexColor(canon)
        except Exception:
            pass
    confidence = (report.get("imara_confidence") or "").capitalize()
    completeness = report.get("imara_completeness")

    _section_header(story, "IMARA SCORE™  ·  BANKABILITY & INVESTABILITY")

    left = Table(
        [
            [Paragraph(str(score), _style(fontSize=44, fontName="Helvetica-Bold",
                                          textColor=col, alignment=TA_CENTER))],
            [Paragraph("OUT OF 100", _style(fontSize=7, textColor=MID_GRAY,
                                            alignment=TA_CENTER, letterSpacing=1))],
            [Paragraph("Band " + str(band) + "  ·  " + str(label),
                       _style(fontSize=9, fontName="Helvetica-Bold",
                              textColor=col, alignment=TA_CENTER))],
            [Paragraph(
                ("Confidence: " + confidence + ("  ·  " + str(completeness) + "% of signals"
                 if completeness is not None else "")) if confidence else "",
                _style(fontSize=7, textColor=MID_GRAY, alignment=TA_CENTER))],
        ],
        colWidths=[CONTENT_W * 0.30],
    )
    left.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.7, col),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    rows = [[
        Paragraph("COMPONENT", _style(fontSize=6.5, fontName="Helvetica-Bold", textColor=WHITE)),
        Paragraph("SCORE", _style(fontSize=6.5, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_CENTER)),
        Paragraph("WEIGHT", _style(fontSize=6.5, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_CENTER)),
    ]]
    comp_tbl_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    ri = 1
    for c in components:
        v = int(round(c.get("value", 0)))
        wpct = int(round(c.get("weight", 0) * 100))
        vc = GREEN if v >= 70 else AMBER if v >= 40 else RED
        rows.append([
            Paragraph(str(c.get("label", "")), _style(fontSize=8, textColor=DARK_GRAY)),
            Paragraph(str(v), _style(fontSize=8, fontName="Helvetica-Bold", textColor=vc, alignment=TA_CENTER)),
            Paragraph(str(wpct) + "%", _style(fontSize=8, textColor=MID_GRAY, alignment=TA_CENTER)),
        ])
        if ri % 2 == 0:
            comp_tbl_style.append(("BACKGROUND", (0, ri), (-1, ri), OFF_WHITE))
        ri += 1

    right = Table(rows, colWidths=[CONTENT_W * 0.42, CONTENT_W * 0.13, CONTENT_W * 0.13])
    right.setStyle(TableStyle(comp_tbl_style))

    outer = Table([[left, right]], colWidths=[CONTENT_W * 0.32, CONTENT_W * 0.68])
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
    ]))
    story.append(outer)
    story.append(Spacer(1, 0.5 * cm))


def _financial_ratios_section(story, report):
    """Grounded financial ratios table — computed from the financials, traceable."""
    ratios = report.get("financial_ratios", {}) or {}
    if not ratios:
        return
    fund = report.get("financial_fundamentals_score")
    title = "FINANCIAL FUNDAMENTALS"
    if fund:
        title += "  ·  SCORE " + str(fund) + "/100"
    _section_header(story, title)
    story.append(Paragraph(
        "Computed directly from the financial statements (arithmetic, not AI-generated). "
        "Each figure is traceable to its source line items.",
        _style(fontSize=8, textColor=MID_GRAY, leading=11)))
    story.append(Spacer(1, 0.2 * cm))

    stat_col = {"good": GREEN, "warning": AMBER, "critical": RED}
    head = [Paragraph(h, _style(fontSize=6.5, fontName="Helvetica-Bold", textColor=WHITE))
            for h in ("METRIC", "VALUE", "BENCHMARK", "STATUS", "SOURCE FIGURES")]
    rows = [head]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    ri = 1
    for _k, r in ratios.items():
        v = r.get("value")
        unit = r.get("unit", "")
        val = ("%g%s" % (v, unit)) if v is not None else "—"
        col = stat_col.get(r.get("status"), MID_GRAY)
        rows.append([
            Paragraph(str(r.get("label", "")), _style(fontSize=8, fontName="Helvetica-Bold", textColor=NAVY)),
            Paragraph(val, _style(fontSize=8, fontName="Helvetica-Bold", textColor=col)),
            Paragraph(str(r.get("benchmark", "")), _style(fontSize=8, textColor=DARK_GRAY)),
            Paragraph(str(r.get("status", "")).title(), _style(fontSize=8, textColor=col)),
            Paragraph(str(r.get("source", "")), _style(fontSize=7, textColor=MID_GRAY)),
        ])
        if ri % 2 == 0:
            style.append(("BACKGROUND", (0, ri), (-1, ri), OFF_WHITE))
        ri += 1
    t = Table(rows, colWidths=[CONTENT_W * 0.22, CONTENT_W * 0.13, CONTENT_W * 0.15,
                               CONTENT_W * 0.13, CONTENT_W * 0.37])
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))


# ── Traffic Light Scorecard ────────────────────────────────────────


def _traffic_light_section(story, report):
    _section_header(story, "AT-A-GLANCE SCORECARD")

    scores = report.get("scores", {})
    cur = report.get("currency", "ZAR")

    def _rag(val, lo, hi):
        if val >= hi:
            return GREEN, GREEN_BG
        elif val >= lo:
            return AMBER, AMBER_BG
        return RED, RED_BG

    def _rag_inv(val, lo, hi):
        if val <= lo:
            return GREEN, GREEN_BG
        elif val <= hi:
            return AMBER, AMBER_BG
        return RED, RED_BG

    health  = scores.get("business_health", 0)
    profit  = scores.get("profitability", 0)
    eff     = scores.get("efficiency", 0)
    risk_s  = scores.get("risk", 0)
    credit  = report.get("credit_score", 0)
    fraud_s = report.get("fraud_risk_score", 0)
    val_mid = report.get("valuation_mid", 0)
    fcast   = report.get("forecast_base_12m", 0)
    grade   = report.get("credit_grade", "—")
    fraud_lv = report.get("fraud_risk_level", "unknown").capitalize()
    val_meth = (report.get("valuation_method", "") or "—")[:18]

    val_mid_disp = (cur + " " + "{:,.0f}".format(val_mid)) if val_mid else "—"
    fcast_disp   = (cur + " " + "{:,.0f}".format(fcast))   if fcast   else "—"

    cells = [
        ("Business Health", str(health) + "/100", *_rag(health, 50, 70)),
        ("Profitability",   str(profit) + "/100",  *_rag(profit, 50, 70)),
        ("Efficiency",      str(eff) + "/100",     *_rag(eff, 50, 70)),
        ("Risk Score",      str(risk_s) + "/100",  *_rag(risk_s, 50, 70)),
        ("Credit Score",    str(credit) + "/100",  *_rag(credit, 40, 60)),
        ("Credit Grade",    grade,                 *_rag(credit, 40, 60)),
        ("Fraud Risk",      fraud_lv,              *_rag_inv(fraud_s, 20, 50)),
        ("Fraud Score",     str(fraud_s) + "/100", *_rag_inv(fraud_s, 20, 50)),
        ("Valuation Method", val_meth,              GREEN, GREEN_BG),
        ("Valuation (mid)", val_mid_disp,           GREEN, GREEN_BG),
        ("12m Forecast",    fcast_disp,             GREEN, GREEN_BG),
        ("Total Findings",  str(report.get("total_findings", 0)),
         *_rag_inv(report.get("critical_findings", 0), 0, 2)),
    ]

    col_w = CONTENT_W / 4
    tbl_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, 1), OFF_WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]

    for start in (0, 4, 8):
        hrow, vrow = [], []
        font_sz = 14 if start == 8 else 16
        for label, val_str, col, bg in cells[start:start + 4]:
            hrow.append(Paragraph(
                label, _style(fontSize=7, fontName="Helvetica-Bold",
                              textColor=WHITE, alignment=TA_CENTER)
            ))
            vrow.append(Paragraph(
                val_str, _style(fontSize=font_sz, fontName="Helvetica-Bold",
                                textColor=col, alignment=TA_CENTER)
            ))
        g = Table([hrow, vrow], colWidths=[col_w] * 4)
        g.setStyle(TableStyle(tbl_style))
        story.append(g)
        if start < 8:
            story.append(Spacer(1, 0.2 * cm))

    # RAG legend
    story.append(Spacer(1, 0.4 * cm))
    legend = Table(
        [[Paragraph(
            '<font color="#1A7A40">■</font> Good  '
            '<font color="#C9820A">■</font> Caution  '
            '<font color="#C0392B">■</font> Action Required',
            _style(fontSize=7.5, textColor=MID_GRAY, alignment=TA_CENTER)
        )]],
        colWidths=[CONTENT_W],
    )
    story.append(legend)


# ── Credit Readiness Section ──────────────────────────────────────


def _credit_readiness_section(story, report):
    _section_header(story, "CREDIT READINESS ASSESSMENT")

    cur          = report.get("currency", "ZAR")
    credit_score = report.get("credit_score", 0)
    credit_grade = report.get("credit_grade", "—")
    barriers     = report.get("credit_barriers", [])
    strengths    = report.get("credit_strengths", [])
    products     = report.get("credit_products", [])

    grade_color = {
        "A": GREEN, "B": colors.HexColor("#1A7A40"),
        "C": AMBER,  "D": ORANGE, "F": RED,
    }.get(credit_grade, MID_GRAY)
    score_color = GREEN if credit_score >= 60 else (AMBER if credit_score >= 40 else RED)
    grade_desc  = {
        "A": "Excellent — strong lending candidate",
        "B": "Good — minor concerns, manageable risk",
        "C": "Fair — conditional approval likely",
        "D": "Poor — significant barriers to credit",
        "F": "Fail — fundamental issues must be resolved",
    }.get(credit_grade, "Insufficient data for grading")

    score_hex = _hex(score_color)
    grade_hex = _hex(grade_color)
    score_tbl = Table(
        [[
            Paragraph(
                ('<font size="42" color="#' + score_hex + '"><b>' + str(credit_score) + '</b></font>'
                 '<br/><font size="8" color="#888888">Credit Readiness Score  /100</font>'),
                _style(fontSize=42, alignment=TA_CENTER, leading=50)
            ),
            Paragraph(
                ('<font size="56" color="#' + grade_hex + '"><b>' + credit_grade + '</b></font>'
                 '<br/><font size="8" color="#555555">' + grade_desc + '</font>'),
                _style(fontSize=56, alignment=TA_CENTER, leading=60)
            ),
        ]],
        colWidths=[CONTENT_W / 2, CONTENT_W / 2],
    )
    score_bg = GREEN_BG if credit_score >= 60 else (AMBER_BG if credit_score >= 40 else RED_BG)
    score_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), score_bg),
        ("BACKGROUND", (1, 0), (1, 0), GREEN_BG if credit_grade in ("A", "B") else
                                        (AMBER_BG if credit_grade == "C" else RED_BG)),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Strengths vs barriers
    if strengths or barriers:
        max_rows = max(len(strengths), len(barriers))
        s_rows = strengths + [""] * (max_rows - len(strengths))
        b_rows = barriers  + [""] * (max_rows - len(barriers))
        sb_data = [
            [
                Paragraph("STRENGTHS", _style(fontSize=7, fontName="Helvetica-Bold",
                                              textColor=GREEN, letterSpacing=1)),
                Paragraph("BARRIERS", _style(fontSize=7, fontName="Helvetica-Bold",
                                             textColor=RED, letterSpacing=1)),
            ]
        ]
        for s, b in zip(s_rows, b_rows):
            sb_data.append([
                Paragraph(s, _style(fontSize=8, textColor=DARK_GRAY)) if s else Paragraph("", _style()),
                Paragraph(b, _style(fontSize=8, textColor=DARK_GRAY)) if b else Paragraph("", _style()),
            ])
        sb_tbl = Table(sb_data, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
        sb_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), GREEN_BG),
            ("BACKGROUND", (1, 0), (1, 0), RED_BG),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F0FBF4")),
            ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#FDF4F3")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(sb_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Funding products
    if products:
        prod_str = "  ·  ".join(products)
        story.append(Paragraph(
            "RECOMMENDED FUNDING PRODUCTS",
            _style(fontSize=7, fontName="Helvetica-Bold", textColor=NAVY, letterSpacing=1)
        ))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            prod_str,
            _style(fontSize=9, textColor=DARK_GRAY)
        ))


# ── Valuation Section ─────────────────────────────────────────────


def _valuation_section(story, report):
    _section_header(story, "BUSINESS VALUATION")

    cur      = report.get("currency", "ZAR")
    val_low  = report.get("valuation_low", 0)
    val_mid  = report.get("valuation_mid", 0)
    val_high = report.get("valuation_high", 0)
    method   = report.get("valuation_method", "—") or "—"
    multiple = report.get("valuation_ebitda_multiple", 0)
    ebitda   = report.get("normalised_ebitda", 0)
    rev      = report.get("annual_revenue", 0)

    def _fv(v):
        if not v:
            return "—"
        if v >= 1_000_000:
            return cur + " " + "{:.1f}M".format(v / 1_000_000)
        if v >= 1_000:
            return cur + " " + "{:.0f}K".format(v / 1_000)
        return cur + " " + "{:.0f}".format(v)

    bear_str = _fv(val_low)
    base_str = _fv(val_mid)
    bull_str = _fv(val_high)

    val_data = [
        [
            Paragraph("BEAR CASE", _style(fontSize=7, fontName="Helvetica-Bold",
                                          textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("BASE CASE", _style(fontSize=7, fontName="Helvetica-Bold",
                                          textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("BULL CASE", _style(fontSize=7, fontName="Helvetica-Bold",
                                          textColor=WHITE, alignment=TA_CENTER)),
        ],
        [
            Paragraph(bear_str, _style(fontSize=18, fontName="Helvetica-Bold",
                                       textColor=RED, alignment=TA_CENTER)),
            Paragraph(base_str, _style(fontSize=18, fontName="Helvetica-Bold",
                                       textColor=NAVY, alignment=TA_CENTER)),
            Paragraph(bull_str, _style(fontSize=18, fontName="Helvetica-Bold",
                                       textColor=GREEN, alignment=TA_CENTER)),
        ],
    ]
    col3 = CONTENT_W / 3
    val_tbl = Table(val_data, colWidths=[col3] * 3)
    val_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (0, 1), RED_BG),
        ("BACKGROUND", (1, 1), (1, 1), OFF_WHITE),
        ("BACKGROUND", (2, 1), (2, 1), GREEN_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(val_tbl)
    story.append(Spacer(1, 0.3 * cm))

    # Methodology detail rows
    mult_str   = "{:.1f}x".format(multiple) if multiple else "—"
    ebitda_str = _fv(ebitda)
    rev_str    = _fv(rev)
    detail_data = [
        ["Valuation Method", method],
        ["EBITDA Multiple", mult_str],
        ["Normalised EBITDA", ebitda_str],
        ["Annual Revenue", rev_str],
    ]
    det_tbl = Table(detail_data, colWidths=[CONTENT_W * 0.4, CONTENT_W * 0.6])
    det_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [OFF_WHITE, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(det_tbl)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Indicative only. Engage a registered Business Valuator (SAVCA/SAICA) for a formal opinion.",
        _style(fontSize=7.5, textColor=MID_GRAY, leading=11)
    ))


# ── Forecast Section ─────────────────────────────────────────────


def _forecast_section(story, report):
    """12-month scenario forecast."""
    cur   = report.get("currency", "ZAR")
    base  = report.get("forecast_base_12m", 0)
    bull  = report.get("forecast_bull_12m", 0)
    bear  = report.get("forecast_bear_12m", 0)
    assns = report.get("forecast_assumptions", [])

    if not any([base, bull, bear]):
        return

    _section_header(story, "12-MONTH REVENUE FORECAST")

    def _fv(v):
        if not v:
            return "—"
        if v >= 1_000_000:
            return cur + " " + "{:.1f}M".format(v / 1_000_000)
        return cur + " " + "{:,.0f}".format(v)

    f_data = [
        [
            Paragraph("BULL SCENARIO", _style(fontSize=7, fontName="Helvetica-Bold",
                                              textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("BASE SCENARIO", _style(fontSize=7, fontName="Helvetica-Bold",
                                              textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("BEAR SCENARIO", _style(fontSize=7, fontName="Helvetica-Bold",
                                              textColor=WHITE, alignment=TA_CENTER)),
        ],
        [
            Paragraph(_fv(bull), _style(fontSize=16, fontName="Helvetica-Bold",
                                        textColor=GREEN, alignment=TA_CENTER)),
            Paragraph(_fv(base), _style(fontSize=16, fontName="Helvetica-Bold",
                                        textColor=GOLD, alignment=TA_CENTER)),
            Paragraph(_fv(bear), _style(fontSize=16, fontName="Helvetica-Bold",
                                        textColor=RED, alignment=TA_CENTER)),
        ],
    ]
    col3 = CONTENT_W / 3
    f_tbl = Table(f_data, colWidths=[col3] * 3)
    f_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (0, 1), GREEN_BG),
        ("BACKGROUND", (1, 1), (1, 1), OFF_WHITE),
        ("BACKGROUND", (2, 1), (2, 1), RED_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(f_tbl)

    if assns:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "ASSUMPTIONS",
            _style(fontSize=7, fontName="Helvetica-Bold", textColor=DARK_GRAY, letterSpacing=1)
        ))
        for a in assns:
            story.append(Paragraph(
                "→  " + a,
                _style(fontSize=8, textColor=MID_GRAY, leading=12)
            ))


# ── Fraud Risk Section ────────────────────────────────────────────


def _fraud_risk_section(story, report):
    _section_header(story, "FRAUD & ANOMALY RISK")

    level      = report.get("fraud_risk_level", "unknown")
    score      = report.get("fraud_risk_score", 0)
    indicators = report.get("fraud_indicators", [])

    level_color = {
        "low": GREEN, "medium": AMBER, "high": ORANGE, "critical": RED,
    }.get(level, MID_GRAY)
    level_bg = {
        "low": GREEN_BG, "medium": AMBER_BG, "high": ORANGE_BG, "critical": RED_BG,
    }.get(level, OFF_WHITE)
    desc = {
        "low":      "No significant anomalies detected in financial data.",
        "medium":   "Some irregularities warrant closer review.",
        "high":     "Multiple anomalies detected — formal investigation recommended.",
        "critical": "Significant fraud indicators present — immediate action required.",
    }.get(level, "Insufficient data for fraud risk assessment.")

    badge_data = [
        [
            Paragraph(level.upper() + " RISK",
                      _style(fontSize=22, fontName="Helvetica-Bold",
                             textColor=level_color, alignment=TA_CENTER)),
            Paragraph(str(score) + "/100",
                      _style(fontSize=22, fontName="Helvetica-Bold",
                             textColor=level_color, alignment=TA_CENTER)),
            Paragraph(desc,
                      _style(fontSize=8, textColor=DARK_GRAY, leading=12, alignment=TA_CENTER)),
        ]
    ]
    col3 = CONTENT_W / 3
    badge_tbl = Table(badge_data, colWidths=[col3] * 3)
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), level_bg),
        ("BACKGROUND", (2, 0), (2, 0), OFF_WHITE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(badge_tbl)
    story.append(Spacer(1, 0.4 * cm))

    if indicators:
        story.append(Paragraph(
            "INDICATORS DETECTED",
            _style(fontSize=7, fontName="Helvetica-Bold", textColor=RED, letterSpacing=1)
        ))
        story.append(Spacer(1, 0.15 * cm))
        for i, flag in enumerate(indicators, 1):
            story.append(Paragraph(
                str(i) + ".  " + flag,
                _style(fontSize=8.5, textColor=DARK_GRAY, leading=13)
            ))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        "Findings are indicative anomaly signals, not evidence of criminal conduct. "
        "Engage a Certified Fraud Examiner (CFE) for any formal investigation.",
        _style(fontSize=7.5, textColor=MID_GRAY, leading=11)
    ))


# ── Roadmap Section ───────────────────────────────────────────────


def _roadmap_section(story, report):
    _section_header(story, "90-DAY IMPLEMENTATION ROADMAP")

    roadmap = report.get("implementation_roadmap", [])
    if not roadmap:
        story.append(Paragraph(
            "Roadmap data not available.",
            _style(fontSize=9, textColor=MID_GRAY)
        ))
        return

    phase_colors = [RED, AMBER, GREEN]

    for i, phase in enumerate(roadmap):
        phase_name  = phase.get("phase", "Phase " + str(i + 1))
        focus       = phase.get("focus", "")
        actions     = phase.get("actions", [])
        expected    = phase.get("expected_impact", "")
        priority    = phase.get("priority_level", "").upper()
        col         = phase_colors[i] if i < len(phase_colors) else GREEN

        # Phase header
        hdr_data = [[
            Paragraph(priority or ("PHASE " + str(i + 1)),
                      _style(fontSize=7, fontName="Helvetica-Bold",
                             textColor=col, letterSpacing=1)),
            Paragraph(phase_name,
                      _style(fontSize=10, fontName="Helvetica-Bold", textColor=NAVY)),
        ]]
        hdr_tbl = Table(hdr_data, colWidths=[CONTENT_W * 0.2, CONTENT_W * 0.8])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), OFF_WHITE),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, col),
            ("LEFTBORDER", (0, 0), (0, -1), 3, col),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(KeepTogether([hdr_tbl]))
        story.append(Spacer(1, 0.1 * cm))

        if focus:
            story.append(Paragraph(
                focus,
                _style(fontSize=8.5, textColor=MID_GRAY, leading=12)
            ))
            story.append(Spacer(1, 0.15 * cm))

        # Actions
        for act in actions:
            action_text = act.get("action", str(act)) if isinstance(act, dict) else str(act)
            owner       = act.get("owner", "") if isinstance(act, dict) else ""
            impact      = act.get("impact", "") if isinstance(act, dict) else ""
            line = "→  " + action_text
            if owner:
                line += "   [" + owner + "]"
            story.append(Paragraph(
                line,
                _style(fontSize=8.5, textColor=DARK_GRAY, leading=13)
            ))
            if impact:
                story.append(Paragraph(
                    "   " + impact,
                    _style(fontSize=8, textColor=col, leading=11)
                ))

        if expected:
            story.append(Spacer(1, 0.15 * cm))
            story.append(Paragraph(
                "Expected impact: " + expected,
                _style(fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)
            ))

        story.append(Spacer(1, 0.4 * cm))


# ── Closing Section ───────────────────────────────────────────────


def _closing_section(story, report):
    story.append(PageBreak())
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        "BUSINESS FORENSICS AI",
        _style(fontSize=11, fontName="Helvetica-Bold", textColor=GOLD,
               letterSpacing=3, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="60%", thickness=0.5, color=GOLD))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "CONFIDENTIALITY NOTICE",
        _style(fontSize=8, fontName="Helvetica-Bold", textColor=DARK_GRAY,
               letterSpacing=2, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "This report has been prepared by Imara and is intended solely for the "
        "use of the named recipient(s). The information contained herein is confidential and "
        "may not be reproduced, distributed, or disclosed to any third party without the prior "
        "written consent of the issuing party. All findings, scores, valuations, and forecasts "
        "are based on AI analysis of the data provided and are indicative only.",
        _style(fontSize=8.5, textColor=MID_GRAY, leading=13, alignment=TA_JUSTIFY)
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Financial projections and valuations do not constitute advice and should not be "
        "relied upon as the sole basis for any business, investment, or lending decision. "
        "Engage qualified professionals \u2014 CA(SA), CFE, registered valuator \u2014 for formal opinions.",
        _style(fontSize=8.5, textColor=MID_GRAY, leading=13, alignment=TA_JUSTIFY)
    ))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(
        date.today().strftime("%d %B %Y"),
        _style(fontSize=8, textColor=DARK_GRAY, alignment=TA_CENTER)
    ))
